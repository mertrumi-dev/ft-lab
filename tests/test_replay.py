"""Replay check of the mini bot's demo loop (scripts/replay.py).

Fast tests: the ReplayExchange fill rules and the Freqtrade-equal entry gates.
Slow test (real candles + the stored Freqtrade backtest; skipped unless FTLAB_SLOW=1):
    FTLAB_SLOW=1 python3 scripts/ft.py test tests/test_replay.py
"""

import os
import sys
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import replay  # noqa: E402
from minibot import paper  # noqa: E402

H = replay.HOUR_MS


def ex_with(row):
    ex = replay.ReplayExchange({"BTC/USDT": [[0, 1, 1, 1, 1, 1], row]}, fee=0.001)
    ex.now_ms = H
    return ex


def test_replay_limit_fills_inside_the_next_candle():
    ex = ex_with([H, 100.0, 105.0, 95.0, 101.0, 1.0])  # open 100, high 105, low 95
    assert ex.create_order("BTC/USDT", "limit", "buy", 1, 101, {})["average"] == 100.0  # open already better
    assert ex.create_order("BTC/USDT", "limit", "buy", 1, 97, {})["average"] == 97.0  # touched later
    assert ex.create_order("BTC/USDT", "limit", "buy", 1, 94, {})["status"] == "open"  # never reached
    assert ex.create_order("BTC/USDT", "limit", "sell", 1, 99, {})["average"] == 100.0
    assert ex.create_order("BTC/USDT", "limit", "sell", 1, 106, {})["status"] == "open"
    o = ex.create_order("BTC/USDT", "limit", "sell", 2, 104, {})
    assert o["fee"] == {"cost": pytest.approx(2 * 104 * 0.001), "currency": "USDT"}


def test_replay_serves_only_closed_candles():
    ex = ex_with([H, 100.0, 105.0, 95.0, 101.0, 1.0])
    assert [r[0] for r in ex.fetch_ohlcv("BTC/USDT", "1h", 1000)] == [0]  # candle H is still forming


def test_freqtrade_gates_max_open_cooldown_inclusive_and_stop_guard():
    acc = paper.new_account(1000)
    for p in ("A", "B", "C"):
        acc["positions"][p] = {}
    assert paper.entry_blocked(acc, "D", 0) == "max open trades"
    acc["positions"].clear()
    paper.after_close(acc, "A", 10 * H, "ema_cross_down")
    assert paper.entry_blocked(acc, "A", 12 * H) == "cooldown"  # end hour included (Freqtrade backtest)
    assert paper.entry_blocked(acc, "A", 13 * H) is None and paper.entry_blocked(acc, "B", 11 * H) is None
    for t in (20, 30, 40):
        paper.after_close(acc, "X", t * H, "stoploss")
    assert paper.entry_blocked(acc, "B", 52 * H) == "stoploss guard" and paper.entry_blocked(acc, "B", 53 * H) is None


@pytest.mark.skipif(os.environ.get("FTLAB_SLOW") != "1", reason="slow: set FTLAB_SLOW=1 (needs data + backtest results)")
def test_demo_loop_equals_the_backtest_on_fresh():
    import report
    from splits import SLICES

    s = SLICES["fresh"]
    stats = report.latest_stats_per_strategy(s.timerange, replay.CORE, 0.0015, ROOT / "user_data" / "backtest_results" / "no_kill_switch")
    if "TrendEmaVolTarget" not in stats:
        pytest.skip("run: ft.py backtest --slice fresh --no-kill-switch --strategy TrendEmaVolTarget")
    data = ROOT / "user_data" / "data" / "binance"
    candles = {}
    for pair in replay.CORE:
        df = pd.read_feather(data / f"{pair.replace('/', '_')}-1h.feather")
        ms = pd.to_datetime(df["date"], utc=True).astype("datetime64[ms, UTC]").astype("int64")
        candles[pair] = [[int(t), o, h, lo, c, v] for t, o, h, lo, c, v in
                         zip(ms, df["open"], df["high"], df["low"], df["close"], df["volume"])]  # fmt: skip
    start = int(pd.Timestamp(s.start, tz="UTC").value // 10**6)
    end = min(int(pd.Timestamp(s.end, tz="UTC").value // 10**6), max(r[0] for r in candles["BTC/USDT"]) + H)
    state = replay.run_replay(candles, start, end, 0.0015)
    c = replay.compare(replay.minibot_trades(state), stats["TrendEmaVolTarget"]["trades"])
    assert not c["only_ft"] and not c["only_mini"]  # same entries, hour by hour
    assert "other 0" in replay.exit_kinds(c["matched"])  # exit differences only: stop 1h later / open at end
    errs = sorted(abs(r["mini_stake"] / r["ft_stake"] - 1) for r in c["matched"])
    assert errs[len(errs) // 2] < 0.01  # stake within 1% (median; 0.23% on 2026-11-01, was 5% before tradable_balance_ratio)
    gap = sum(r["mini_profit"] - r["ft_profit"] for r in c["matched"] if r["mini_profit"] is not None)
    assert abs(gap) < 1.0  # P/L of the same trades within 1 USDT (-0.03 on 2026-11-01)
