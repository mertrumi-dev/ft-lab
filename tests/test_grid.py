"""Tests for the grid trading simulator."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import ft  # noqa: E402
import grid  # noqa: E402


def candles(close, high=None, low=None):
    close = np.asarray(close, dtype=float)
    return pd.DataFrame(
        {"high": close if high is None else high, "low": close if low is None else low, "close": close},
        index=pd.date_range("2024-01-01", periods=len(close), freq="1h", tz="UTC"),
    )


def test_flat_price_never_trades_and_keeps_cash():
    eq, trips = grid.simulate_pair(candles([100.0] * 50), 1.0, fee=0.0)
    assert trips == 0 and eq.iloc[-1] == pytest.approx(1.0)


def test_one_round_trip_earns_one_step_minus_fees():
    # down to the first rung (98), then up past its sell price (99.96)
    eq, trips = grid.simulate_pair(candles([100, 98, 100, 100]), 1.0, step=0.02, levels=10, fee=0.0)
    assert trips == 1
    assert eq.iloc[-1] == pytest.approx(1.0 + 0.1 * 0.02)  # one rung = 10% of cash, +2%


def test_no_buy_and_sell_in_the_same_candle():
    # one wild candle touches both 98 and 99.96: buy only, sell must wait
    c = candles([100, 99, 99], high=[100, 100.5, 99], low=[100, 97.9, 99])
    _, trips = grid.simulate_pair(c, 1.0, step=0.02, levels=10, fee=0.0)
    assert trips == 0


def test_crash_fills_every_rung_and_loses():
    eq, _ = grid.simulate_pair(candles(np.linspace(100, 50, 200)), 1.0, fee=0.0)
    assert eq.iloc[-1] < 0.7  # bag of coins bought on the way down


def test_ladder_trails_up_in_a_rally():
    # rally to 150, then a ~3% dip: with a trailing ladder the dip is bought and sold
    close = list(np.linspace(100, 150, 100)) + [145.0, 150.0]
    _, trips = grid.simulate_pair(candles(close), 1.0, fee=0.0)
    assert trips == 1


def test_fees_make_tiny_steps_lose():
    zig = [100, 99.7, 100.0] * 100
    eq, trips = grid.simulate_pair(candles(zig), 1.0, step=0.002, levels=10, fee=0.0015)
    assert trips > 50 and eq.iloc[-1] < 1.0  # 0.2% step < 0.3% round-trip fee


def test_ft_bots_never_on_test_slice():
    with pytest.raises(SystemExit):
        ft.parse_args(["bots", "--slice", "test"])
    (cmd,) = ft.build_commands(ft.parse_args(["bots", "--slice", "train", "--no-kill-switch"]))
    assert "/freqtrade/scripts/bots.py" in cmd and f"/freqtrade/{ft.NO_KILL_DIR}" in cmd
    assert "TrendEma" in cmd and "NostalgiaForInfinityX8" in cmd


# --- 3Commas-style DCA bot -------------------------------------------------
import dcabot  # noqa: E402


def test_dca_ladder_levels_and_sizes():
    drops, sizes = dcabot.ladder()
    assert list(drops.round(4)) == [0.02, 0.05, 0.095, 0.1625, 0.2638]
    assert list(sizes) == [1.0, 1.0, 1.5, 2.25, 3.375, 5.0625]


def test_dca_bot_take_profit_restarts_deal():
    # start 100, rises 2% -> deal closes with +1.5% on the base order, new deal opens
    eq, deals = dcabot.simulate_pair(candles([100, 102, 102]), 1.0, fee=0.0)
    _, sizes = dcabot.ladder()
    assert deals == 1
    assert eq.iloc[-1] == pytest.approx(1.0 + 0.015 / sizes.sum(), rel=1e-6)


def test_dca_bot_buys_safety_orders_and_lowers_average():
    # start 100, dip to 98 (SO1), then 99.5 is enough to take profit on the average 99
    eq, deals = dcabot.simulate_pair(candles([100, 98, 100.5]), 1.0, fee=0.0)
    assert deals == 1 and eq.iloc[-1] > 1.0


def test_dca_bot_holds_bag_in_a_crash_without_stop():
    eq, deals = dcabot.simulate_pair(candles(np.linspace(100, 40, 300)), 1.0, fee=0.0)
    assert deals == 0 and eq.iloc[-1] < 0.6  # all safety orders filled, no stop


def test_dca_bot_never_spends_more_than_its_cash():
    eq, _ = dcabot.simulate_pair(candles(np.linspace(100, 10, 300)), 1.0, fee=0.0015)
    assert eq.min() > 0


def test_bots_table_simulates_every_coin_with_data(tmp_path):
    import bots

    idx = pd.date_range("2021-01-01", periods=500, freq="1h", tz="UTC")
    close = 100 + 5 * np.sin(np.arange(500) / 10)  # sideways market
    for pair in ("BTC_USDT", "ETH_USDT"):
        pd.DataFrame({"date": idx, "open": close, "high": close + 1, "low": close - 1,
                      "close": close, "volume": 1.0}).to_feather(tmp_path / f"{pair}-1h.feather")  # fmt: skip
    r = bots.simulate_bot(dcabot.simulate_pair, "train", "core", 0.0015, data_dir=tmp_path)
    assert r["trades"] > 10 and r["total_return"] > 0  # sideways = good for DCA bots
    g = bots.simulate_bot(lambda c, cash, fee: grid.simulate_pair(c, cash, fee=fee),
                          "train", "core", 0.0015, data_dir=tmp_path)  # fmt: skip
    assert g["trades"] > 10
