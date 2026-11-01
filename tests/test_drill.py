"""Kill-switch drill (scripts/drill.py): made-up data properties + the mini bot's behaviour.

The full drill (with the Freqtrade backtest) is `python3 scripts/ft.py drill`.
The mini bot part is slow (~1 min): FTLAB_SLOW=1 python3 scripts/ft.py test tests/test_drill.py
"""

import os
import sys
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import drill  # noqa: E402


def test_drill_data_is_made_up_and_shaped_as_described():
    c = drill.make_candles()
    assert set(c) == set(drill.PAIRS)
    btc = c["BTC/USDT"]
    assert btc["date"].iloc[0] == pd.Timestamp(drill.START, tz="UTC") and btc["date"].iloc[0].year == 2029  # never real data
    i = drill.WARMUP_H + 88  # crash week: after the dip (40h) and the rise (48h)
    fall = btc["close"].iloc[i + 120] / btc["close"].iloc[i] - 1
    assert fall == pytest.approx(-0.35, abs=0.005)  # -35% over 5 days
    assert (btc["low"] <= btc[["open", "close"]].min(axis=1)).all() and (btc["high"] >= btc[["open", "close"]].max(axis=1)).all()
    # realistic price levels: real exchange minimums (XRP 0.1 coin) must not bind (research 08)
    assert c["XRP/USDT"]["close"].max() < 20 and btc["close"].iloc[0] == 50_000.0


def test_kill_point_uses_the_first_20_percent_fall():
    t = lambda p, h: {"close": pd.Timestamp("2030-01-01", tz="UTC") + pd.Timedelta(hours=h), "profit": p}  # noqa: E731
    i, when, dd = drill.kill_point([t(-100, 1), t(-60, 2), t(-50, 3), t(300, 4)])
    assert i == 2 and when.hour == 3 and dd == pytest.approx(0.21)


@pytest.mark.skipif(os.environ.get("FTLAB_SLOW") != "1", reason="slow: set FTLAB_SLOW=1")
def test_minibot_drill_kill_switch_latches_no_entry_after_and_survives_restart(tmp_path):
    import replay

    c = drill.make_candles()

    def closed(state):
        return [{"pair": t["pair"], "open": pd.Timestamp(t["open"]), "close": pd.Timestamp(t["close"]),
                 "profit": round(t["profit"], 6), "reason": t["reason"]}
                for t in replay.minibot_trades(state) if t["close"] is not None]  # fmt: skip

    state = drill.run_minibot(c)
    trades = closed(state)
    s = drill.summarize(trades)
    assert s["kill_time"] is not None and s["kill_dd"] >= 0.20  # the drill really reaches the kill switch
    assert s["crash_week_trades"] == 3 and s["crash_week_pl"] > 0  # slow crash: exited by signal, no kill
    assert s["entries_after"] == []  # latched: nothing opened after it
    assert state["ledger"]["kill_switch"] is True
    restart = int((s["kill_time"] + pd.Timedelta(hours=24)).value // 10**6)
    assert closed(drill.run_minibot(c, restart, tmp_path / "state.demo.json")) == trades  # restart changes nothing
