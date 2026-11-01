"""Health report for the dry-run bot: is it alive, is it erroring, is it near the kill switch?

    python3 scripts/health.py              # last 24 hours
    python3 scripts/health.py --hours 6

Read-only: it reads the bot's log through `docker compose logs`, opens the trade
database read-only and asks Docker for the container status. It never starts,
stops or changes the bot, and never reads .env.

Stdlib only (sqlite3, re, subprocess), so it runs on the Mac without the venv.

Error classes:
  network   websocket/DNS/timeouts talking to Binance. Freqtrade retries these on
            its own; a few per hour are normal, a burst means the Mac lost internet
            or went to sleep.
  other     everything else. Even one of these needs a human look.

Faz 0 verdict = the bot ran >= 24h, its last heartbeat is recent and there was
no "other" error. Network errors are counted and shown, but they do not fail it.
"""

import argparse
import re
import sqlite3
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "user_data" / "tradesv3.dryrun.sqlite"
STARTING_BALANCE = 1000.0  # config.json dry_run_wallet
KILL_SWITCH_DRAWDOWN = 0.20  # same number as trend_ema.py
HEARTBEAT_MAX_AGE = timedelta(minutes=5)  # the bot logs one every minute
PHASE0_HOURS = 24

LINE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ - (\S+) - (\w+) - (.*)$")
# Exception names that mean "could not reach Binance". If any exception in an
# error's traceback chain is one of these, the error counts as a network error.
NETWORK_EXCEPTIONS = (
    "NetworkError", "RequestTimeout", "UnsubscribeError", "CancelledError", "ExchangeNotAvailable",
    "TemporaryError", "gaierror", "ClientConnectorError", "ClientConnectorDNSError", "TimeoutError",
)  # fmt: skip
NETWORK_SOURCES = ("exchange_ws",)
EXCEPTION_LINE = re.compile(r"^([\w.]+(?:Error|Exception|Timeout|error)):")


@dataclass
class LogSummary:
    first_heartbeat: datetime | None = None
    last_heartbeat: datetime | None = None
    network_by_hour: Counter = field(default_factory=Counter)
    network_by_cause: Counter = field(default_factory=Counter)
    other_errors: list[str] = field(default_factory=list)
    restarts: int = 0


def parse_time(text: str) -> datetime:
    """Freqtrade's container logs in UTC."""
    return datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def is_network(source: str, chain: list[str]) -> bool:
    return any(src in source for src in NETWORK_SOURCES) or any(name in NETWORK_EXCEPTIONS for name in chain)


def summarize_log(lines, since: datetime) -> LogSummary:
    """Walk the log once. Each ERROR line is followed by its traceback; the exception
    names in that traceback (the "chain") tell us what went wrong."""
    s = LogSummary()
    pending: tuple[datetime, str, str] | None = None  # error whose traceback we are reading
    chain: list[str] = []

    def close_pending() -> None:
        nonlocal pending
        if pending is None:
            return
        when, source, message = pending
        if is_network(source, chain):
            s.network_by_hour[when.strftime("%Y-%m-%d %H")] += 1
            s.network_by_cause[chain[-1] if chain else "unknown"] += 1
        else:
            s.other_errors.append(f"{when:%Y-%m-%d %H:%M} {source}: {message[:120]}")
        pending = None

    for raw in lines:
        m = LINE.match(raw.rstrip("\n"))
        if not m:
            exc = EXCEPTION_LINE.match(raw)
            if pending is not None and exc:
                chain.append(exc.group(1).rsplit(".", 1)[-1])
            continue
        close_pending()
        when, source, level, message = parse_time(m.group(1)), m.group(2), m.group(3), m.group(4)
        if "Bot heartbeat" in message:
            gap = s.last_heartbeat is not None and when - s.last_heartbeat > HEARTBEAT_MAX_AGE
            if gap:
                s.restarts += 1  # a gap = the bot (or the Mac) was down
            if s.first_heartbeat is None or gap:
                s.first_heartbeat = when  # uptime counts from the latest uninterrupted run
            s.last_heartbeat = when
        if when >= since and level in ("ERROR", "CRITICAL"):
            pending, chain = (when, source, message), []
    close_pending()
    return s


def drawdown_from_peak(starting: float, closed_profits: list[float]) -> float:
    """Same math as trend_ema.drawdown_from_peak (copied: this script must not import freqtrade)."""
    equity = peak = starting
    for profit in closed_profits:
        equity += profit
        peak = max(peak, equity)
    return (peak - equity) / peak if peak > 0 else 0.0


def trade_summary(db: Path) -> dict:
    if not db.exists():
        return {"open": 0, "closed": 0, "profit": 0.0, "drawdown": 0.0}
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)  # read-only: never lock or change the bot's DB
    try:
        open_n = con.execute("select count(*) from trades where is_open = 1").fetchone()[0]
        rows = con.execute(
            "select close_profit_abs from trades where is_open = 0 order by close_date"
        ).fetchall()
    finally:
        con.close()
    profits = [r[0] or 0.0 for r in rows]
    return {
        "open": open_n,
        "closed": len(profits),
        "profit": sum(profits),
        "drawdown": drawdown_from_peak(STARTING_BALANCE, profits),
    }


def read_log_lines() -> list[str]:
    """The bot's log as Docker keeps it (stdout of the container), without the name prefix."""
    out = subprocess.run(
        ["docker", "compose", "logs", "--no-log-prefix", "--no-color", "freqtrade"],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )  # fmt: skip
    return out.stdout.splitlines()


def container_status() -> str:
    try:
        out = subprocess.run(
            ["docker", "compose", "ps", "--format", "{{.Name}} {{.Status}}"],
            cwd=ROOT, capture_output=True, text=True, timeout=30,
        )  # fmt: skip
        return out.stdout.strip() or "not running"
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"unknown ({e.__class__.__name__}: is docker on PATH?)"


def hours(delta: timedelta) -> str:
    return f"{delta.total_seconds() / 3600:.1f}h"


def phase0_verdict(s: LogSummary, now: datetime) -> str:
    if s.last_heartbeat is None:
        return "FAIL: no heartbeat in the log"
    if now - s.last_heartbeat > HEARTBEAT_MAX_AGE:
        return f"FAIL: last heartbeat {hours(now - s.last_heartbeat)} ago (bot down or Mac asleep)"
    if s.other_errors:
        return f"FAIL: {len(s.other_errors)} non-network error(s), see above"
    uptime = now - s.first_heartbeat
    if uptime < timedelta(hours=PHASE0_HOURS):
        return f"NOT YET: running {hours(uptime)} without a gap, needs {PHASE0_HOURS}h"
    return f"PASS: {hours(uptime)} without a gap, no non-network errors"


def render(s: LogSummary, trades: dict, status: str, now: datetime, hours: int) -> str:
    out = [f"Health report {now:%Y-%m-%d %H:%M} UTC (last {hours}h)", f"Container:      {status}"]
    if s.last_heartbeat:
        out.append(f"Last heartbeat: {s.last_heartbeat:%H:%M:%S} UTC ({int((now - s.last_heartbeat).total_seconds())}s ago)")
        out.append(f"Running since:  {s.first_heartbeat:%Y-%m-%d %H:%M} UTC without a gap ({s.restarts} gap(s) in the log)")
    out.append(f"Trades:         {trades['open']} open, {trades['closed']} closed, realized {trades['profit']:+.2f} USDT")
    out.append(
        f"Kill switch:    realized drawdown {trades['drawdown']:.1%} of {KILL_SWITCH_DRAWDOWN:.0%}"
        + ("  <-- TRIGGERED" if trades["drawdown"] >= KILL_SWITCH_DRAWDOWN else "")
    )
    total_net = sum(s.network_by_hour.values())
    out.append(f"Network errors: {total_net}  (normal: a few per hour; a burst = no internet / Mac asleep)" + (f"  ({', '.join(f'{k} {v}' for k, v in s.network_by_cause.most_common())})" if total_net else ""))
    for hour, n in sorted(s.network_by_hour.items()):
        out.append(f"  {hour}h  {n:4d} {'#' * min(n, 50)}")
    out.append(f"Other errors:   {len(s.other_errors)}")
    out.extend(f"  {e}" for e in s.other_errors[-10:])
    out.append(f"Faz 0:          {phase0_verdict(s, now)}")
    out.append("Order quality:  python3 scripts/ft.py execution  (fill rate, slippage, fees, missed entries)")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="read-only health report for the dry-run bot")
    parser.add_argument("--hours", type=int, default=24)
    args = parser.parse_args(argv)
    now = datetime.now(timezone.utc)
    try:
        lines = read_log_lines()
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"could not read docker logs ({e.__class__.__name__}): is docker on PATH?")
        return 1
    s = summarize_log(lines, now - timedelta(hours=args.hours))
    print(render(s, trade_summary(DB), container_status(), now, args.hours))
    return 0


if __name__ == "__main__":
    sys.exit(main())
