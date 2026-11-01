"""Execution report: how well do the bot's orders actually fill? (read-only)

    python3 scripts/ft.py execution                 # every dry-run DB found in user_data/
    python3 scripts/ft.py execution --db user_data/tradesv3.voltarget.dryrun.sqlite

The backtest assumes every order fills at the candle price with a fixed 0.15% cost.
Real (or dry-run) orders do not: a limit order can fill a bit worse, fill late or not
fill at all. This report measures that from the bot's own trade database:

  per order    signal price (close of the candle that gave the signal) vs fill price
               = slippage, minutes from order to fill, status
  unfilled     entry orders that were cancelled/expired without a fill, and how much the
               price moved 1h and 24h later (= what the missed entry would have earned)
  summary      fill rate, average slippage, total fees, cost of missed entries

It is the measurement tool for the Phase 5 post-only decision (docs/research/05).
The database is opened read-only (sqlite uri mode=ro), so the running bot is never touched.
Candle prices come from user_data/data/binance/*-1h.feather (pandas, so it runs in Docker).
"""

import argparse
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
USER_DATA = ROOT / "user_data"
DATA_DIR = USER_DATA / "data" / "binance"
DB_GLOB = "*.dryrun.sqlite"


@dataclass
class Order:
    pair: str
    side: str  # buy / sell
    kind: str  # entry / exit / stoploss
    status: str
    requested: float
    fill: float | None
    filled: float
    created: datetime
    filled_at: datetime | None


def _ts(text: str | None) -> datetime | None:
    if not text:
        return None
    return datetime.fromisoformat(str(text).replace("Z", "")).replace(tzinfo=timezone.utc)


def read_orders(db: Path) -> tuple[list[Order], float]:
    """All orders and the total fees paid, from a Freqtrade sqlite DB opened read-only."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "select ft_pair, side, ft_order_side, status, ft_price, average, price, filled, order_date, "
            "order_filled_date from orders order by order_date"
        ).fetchall()
        fees = con.execute(
            "select coalesce(sum(coalesce(fee_open_cost, 0) + coalesce(fee_close_cost, 0)), 0) from trades"
        ).fetchone()[0]
    finally:
        con.close()
    orders = [
        Order(pair, side or "", kind or "", status or "", float(ft_price or 0), (avg or price) if (filled or 0) > 0 else None,
              float(filled or 0), _ts(od), _ts(fd))
        for pair, side, kind, status, ft_price, avg, price, filled, od, fd in rows
    ]  # fmt: skip
    return orders, float(fees or 0)


def signal_candle(created: datetime) -> datetime:
    """Open time of the last 1h candle that was CLOSED when the order was created."""
    return created.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)


def slippage(side: str, signal: float, fill: float) -> float:
    """Positive = worse than the signal price (paid more on a buy, got less on a sell)."""
    return fill / signal - 1 if side == "buy" else signal / fill - 1


def summarize(orders: list[Order], fees: float, price_at) -> dict:
    """price_at(pair, when) -> 1h close at/after `when`, or None. Kept as a function so tests need no data."""
    filled = [o for o in orders if o.fill]
    entries = [o for o in orders if o.kind == "entry"]
    missed = [o for o in entries if not o.fill and o.status in ("canceled", "cancelled", "expired", "rejected")]
    slips, waits = [], []
    for o in filled:
        sig = price_at(o.pair, signal_candle(o.created))
        if sig:
            slips.append(slippage(o.side, sig, o.fill))
        if o.filled_at:
            waits.append((o.filled_at - o.created).total_seconds() / 60)
    missed_moves = {"1h": [], "24h": []}
    for o in missed:
        for label, delta in (("1h", timedelta(hours=1)), ("24h", timedelta(hours=24))):
            later = price_at(o.pair, o.created + delta)
            if later and o.requested:
                missed_moves[label].append(later / o.requested - 1)
    avg = lambda xs: sum(xs) / len(xs) if xs else None  # noqa: E731
    return {
        "orders": len(orders), "filled": len(filled), "entries": len(entries), "missed_entries": len(missed),
        "fill_rate_entries": (len(entries) - len(missed)) / len(entries) if entries else None,
        "avg_slippage": avg(slips), "avg_minutes_to_fill": avg(waits), "fees": fees,
        "missed_move_1h": avg(missed_moves["1h"]), "missed_move_24h": avg(missed_moves["24h"]),
    }  # fmt: skip


def render(name: str, s: dict) -> str:
    pct = lambda v: "-" if v is None else f"{v:+.3%}"  # noqa: E731
    if s["orders"] == 0:
        return f"{name}: no orders yet (the bot has not traded). Nothing to measure."
    fr = "-" if s["fill_rate_entries"] is None else f"{s['fill_rate_entries']:.1%}"
    wait = "-" if s["avg_minutes_to_fill"] is None else f"{s['avg_minutes_to_fill']:.1f} min"
    return "\n".join([
        f"{name}: {s['orders']} orders, {s['filled']} filled",
        f"  entry fill rate     {fr}  ({s['entries'] - s['missed_entries']} of {s['entries']} entry orders filled)",
        f"  avg slippage        {pct(s['avg_slippage'])}  (fill vs close of the signal candle; + = worse)",
        f"  avg time to fill    {wait}",
        f"  fees paid           {s['fees']:.2f} USDT",
        f"  missed entries      {s['missed_entries']}  price 1h later {pct(s['missed_move_1h'])}, 24h later {pct(s['missed_move_24h'])}"
        "  (+ = the missed entry would have gained)",
    ])  # fmt: skip


def candle_lookup(data_dir: Path = DATA_DIR):
    """price_at(pair, when): 1h close of the candle that opens at `when` (pandas, in Docker)."""
    import pandas as pd

    cache: dict[str, "pd.Series"] = {}

    def price_at(pair: str, when: datetime) -> float | None:
        if pair not in cache:
            path = data_dir / f"{pair.replace('/', '_')}-1h.feather"
            cache[pair] = pd.read_feather(path).set_index("date")["close"] if path.exists() else pd.Series(dtype=float)
        s = cache[pair]
        if s.empty:
            return None
        after = s[s.index >= pd.Timestamp(when)]
        return float(after.iloc[0]) if len(after) else None

    return price_at


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="execution report from the dry-run DB (read-only)")
    p.add_argument("--db", type=Path, action="append", help="sqlite file; default: every user_data/*.dryrun.sqlite")
    a = p.parse_args(argv)
    dbs = a.db or sorted(USER_DATA.glob(DB_GLOB))
    if not dbs:
        print("no dry-run database found in user_data/")
        return 0
    price_at = candle_lookup()
    for db in dbs:
        orders, fees = read_orders(db)
        print(render(db.name, summarize(orders, fees, price_at)))
    print("Read-only report. Use it with docs/research/05-maliyet-onerisi.md (post-only decision).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
