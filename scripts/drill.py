"""Kill-switch drill: a made-up crash, run through BOTH bots (Freqtrade backtest and the mini bot).

    python3 scripts/ft.py drill        # generate data -> Freqtrade backtest (kill switch ON) -> compare

Synthetic 1h candles for the core 5 coins (written to user_data/data/drill, never mixed with
real data), in the year 2030 so no real candle can be confused with them:
  1. warm-up: a calm uptrend (EMA200 below the price, so the rule may buy)
  2. "crash week": entries, then every coin falls 35% over 5 days
     -> stops fire, but with 1% risk per trade and at most 3 trades this costs only ~3%:
        the kill switch must NOT fire here (that is the design, R1 + R2 + R4)
  3. "whipsaw": over and over a rise (entry signal) and then a sudden fall through the -8%
     stop; each round costs ~1% per open trade until realized equity is 20% below its peak
     -> the kill switch MUST fire: no new entries after that, open trades keep their stop/exit
Checks (both bots): same entries, the kill switch fires after the same trade, no entry after
it, the mini bot's refusal survives a restart (state file saved and loaded mid-way).
"""

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

PAIRS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]
# Realistic price LEVELS: the backtest applies the real Binance market limits (min quantity),
# and e.g. XRP's 0.1 minimum at a made-up price of 440 means a 46 USDT minimum order, which
# silently skipped small VolTarget entries (docs/research/08). The shape of the path is the same.
BASE_PRICE = {"BTC/USDT": 50_000.0, "ETH/USDT": 3_000.0, "SOL/USDT": 150.0, "BNB/USDT": 500.0, "XRP/USDT": 1.0}
START = "2029-10-01"  # warm-up starts here; the drill window starts at TIMERANGE
TIMERANGE = "20291215-20300601"
WARMUP_H = 24 * 75  # calm uptrend until mid-December 2029
CRASH_WEEK_H = 24 * 12  # entries, then -35% over 5 days, then a flat pause
CYCLE_H = 120  # one whipsaw round
CYCLES = 30
DRILL_DIR = ROOT / "user_data" / "data" / "drill"
# Hours between the coins' rounds. Chosen so no coin's crash candle is another coin's entry
# candle: Freqtrade's backtest would reuse that slot inside the same candle (a backtest-only
# effect, see docs/research/08), and the drill is about the kill switch, not about that.
OFFSET_H = 13  # 2026-11-01: the only tried value (3/5/9/11/13/17) with no clash AND the kill switch reached


def path_for(offset: int) -> np.ndarray:
    """Closes of one coin. `offset` shifts the whipsaw rounds so the coins are not identical."""
    p = [100.0]
    for _ in range(WARMUP_H):
        p.append(p[-1] * 1.0006)  # +0.06%/h, about +4% per 3 days
    # crash week: a short dip (EMA20 under EMA50), a fresh rise (cross up = entry),
    # then -35% over 5 days (120h), then flat
    for _ in range(40):
        p.append(p[-1] * 0.998)
    for _ in range(48):
        p.append(p[-1] * 1.004)
    for _ in range(120):
        p.append(p[-1] * (0.65 ** (1 / 120)))
    for _ in range(CRASH_WEEK_H - 208):
        p.append(p[-1] * 1.0002)
    # whipsaw: dip (EMA20 under EMA50), rise (cross up -> entry), crash through the stop, recover
    for _ in range(offset):
        p.append(p[-1])
    for _ in range(CYCLES):
        for _ in range(40):
            p.append(p[-1] * 0.998)
        for _ in range(30):
            p.append(p[-1] * 1.006)
        p.append(p[-1] * 0.80)  # one candle: -20%, through the -8% stop of the entry
        for _ in range(CYCLE_H - 71):
            p.append(p[-1] * 1.0047)
    return np.array(p)


def make_candles():
    """{pair: DataFrame(date, open, high, low, close, volume)} with the drill's made-up prices."""
    import pandas as pd

    out = {}
    for k, pair in enumerate(PAIRS):
        close = path_for(offset=OFFSET_H * k) * BASE_PRICE[pair] / 100.0
        n = len(close)
        open_ = np.r_[close[0], close[:-1]]
        high = np.maximum(open_, close) * 1.001
        low = np.minimum(open_, close) * 0.999
        dates = pd.date_range(START, periods=n, freq="1h", tz="UTC")
        out[pair] = pd.DataFrame({"date": dates, "open": open_, "high": high, "low": low, "close": close, "volume": 1000.0})
    return out


def write(candles, directory: Path = DRILL_DIR) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for pair, df in candles.items():
        df.to_feather(directory / f"{pair.replace('/', '_')}-1h.feather")


def as_rows(candles) -> dict[str, list[list[float]]]:
    import pandas as pd

    rows = {}
    for pair, df in candles.items():
        ms = pd.to_datetime(df["date"], utc=True).astype("datetime64[ms, UTC]").astype("int64")
        rows[pair] = [[int(t), o, h, lo, c, v] for t, o, h, lo, c, v in
                      zip(ms, df["open"], df["high"], df["low"], df["close"], df["volume"])]  # fmt: skip
    return rows


def run_minibot(candles, restart_at_ms: int | None = None, state_file: Path | None = None) -> dict:
    """The mini bot's demo loop over the drill data; optionally save + reload its state mid-way."""
    import pandas as pd

    import replay
    from minibot import demo

    rows = as_rows(candles)
    start = int(pd.Timestamp(TIMERANGE.split("-")[0], tz="UTC").value // 10**6)
    end = int(pd.Timestamp(TIMERANGE.split("-")[1], tz="UTC").value // 10**6)
    if restart_at_ms is None:
        return replay.run_replay(rows, start, end, 0.0015, pairs=PAIRS)
    ex = replay.ReplayExchange(rows, 0.0015)  # the exchange (and its stop orders) outlives the bot
    first = replay.run_replay(rows, start, restart_at_ms, 0.0015, pairs=PAIRS, exchange=ex)
    demo.save_state(first, state_file)  # "the bot process stops here"
    loaded = demo.load_state(state_file)  # "a new process starts and reads only the file"
    return replay.run_replay(rows, restart_at_ms, end, 0.0015, pairs=PAIRS, state=loaded, exchange=ex)


def kill_point(trades: list[dict], start_balance: float = 1000.0, limit: float = 0.20):
    """(index, close time) of the first closed trade after which realized equity is >= 20% below its peak."""
    eq, peak = start_balance, start_balance
    for i, t in enumerate(sorted(trades, key=lambda t: t["close"])):
        eq += t["profit"]
        peak = max(peak, eq)
        if (peak - eq) / peak >= limit:
            return i, t["close"], (peak - eq) / peak
    return None, None, None


def main() -> int:  # pragma: no cover - runs inside the container
    import pandas as pd

    import report
    import replay

    mode = sys.argv[1] if len(sys.argv) > 1 else "compare"
    candles = make_candles()
    if mode == "generate":
        write(candles)
        print(f"drill data written to {DRILL_DIR} ({len(candles['BTC/USDT'])} hourly candles per coin)")
        return 0
    ft_stats = report.latest_stats_per_strategy(TIMERANGE, PAIRS, 0.0015, ROOT / "user_data" / "backtest_results" / "drill")
    ft = ft_stats.get("TrendEmaVolTarget")
    if not ft:
        print("no drill backtest found: run python3 scripts/ft.py drill")
        return 1
    ft_trades = [{"pair": t["pair"], "open": pd.Timestamp(t["open_date"]), "close": pd.Timestamp(t["close_date"]),
                  "profit": t["profit_abs"], "reason": t["exit_reason"]} for t in ft["trades"]]  # fmt: skip
    def closed(state):
        return [{"pair": t["pair"], "open": pd.Timestamp(t["open"]), "close": pd.Timestamp(t["close"]),
                 "profit": round(t["profit"], 6), "reason": t["reason"]}
                for t in replay.minibot_trades(state) if t["close"] is not None]  # fmt: skip

    mini_trades = closed(run_minibot(candles))
    _, kill_at, _ = kill_point(mini_trades)
    restart_ms = int((kill_at + pd.Timedelta(hours=24)).value // 10**6) if kill_at is not None else None
    state_file = Path("/tmp/drill-state.demo.json")
    restarted = closed(run_minibot(candles, restart_ms, state_file)) if restart_ms else mini_trades
    print(report_text(ft_trades, mini_trades, restarted))
    c = replay.compare([{**t, "open": t["open"], "close": t["close"], "stake": 0} for t in mini_trades],
                       [{**t, "open_date": str(t["open"]), "close_date": str(t["close"]), "stake_amount": 1,
                         "profit_abs": t["profit"], "exit_reason": t["reason"]} for t in ft_trades])  # fmt: skip
    print(f"  trade lists: same entry hour {len(c['matched'])}, only Freqtrade {len(c['only_ft'])}, only minibot {len(c['only_mini'])}")
    return 0


def summarize(trades: list[dict]) -> dict:
    import pandas as pd

    i, when, dd = kill_point(trades)
    crash_week_end = pd.Timestamp(START, tz="UTC") + pd.Timedelta(hours=WARMUP_H + CRASH_WEEK_H)
    out = {"trades": len(trades), "kill_index": i, "kill_time": when, "kill_dd": dd,
           "crash_week_pl": sum(t["profit"] for t in trades if t["close"] <= crash_week_end),
           "crash_week_trades": sum(t["close"] <= crash_week_end for t in trades)}  # fmt: skip
    if when is not None:
        out["entries_after"] = [t for t in trades if t["open"] > when]
        out["open_at_kill"] = [t for t in trades if t["open"] <= when < t["close"]]  # closed later by their own exit
    return out


def report_text(ft_trades, mini_trades, restarted_trades) -> str:
    lines = [f"Kill-switch drill ({TIMERANGE}, made-up data, core 5, kill switch ON, offset {OFFSET_H}h)"]
    res = {}
    for name, trades in (("Freqtrade", ft_trades), ("minibot", mini_trades), ("minibot+restart", restarted_trades)):
        r = res[name] = summarize(trades)
        lines.append(f"  {name:<16} trades {r['trades']}; crash week: {r['crash_week_trades']} trades, P/L {r['crash_week_pl']:+.2f} USDT")
        if r["kill_time"] is None:
            lines.append("                   kill switch NOT reached")
            continue
        lines.append(f"                   kill switch after closed trade #{r['kill_index'] + 1} at {r['kill_time']} "
                     f"(realized drawdown {r['kill_dd']:.1%}); entries after it: {len(r['entries_after'])}; "
                     f"open at that moment: {len(r['open_at_kill'])} -> closed later by "
                     f"{sorted({t['reason'] for t in r['open_at_kill']}) or '-'}")  # fmt: skip
    a, b = res["Freqtrade"], res["minibot"]
    same = a["kill_time"] is not None and a["kill_time"] == b["kill_time"]
    lines.append(f"  same kill moment in both bots: {'YES' if same else 'NO'}; "
                 f"restart changed nothing: {'YES' if restarted_trades == mini_trades else 'NO'}")  # fmt: skip
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
