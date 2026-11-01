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


def test_ft_bots_test_slice_needs_final_test_flag():
    with pytest.raises(SystemExit):
        ft.build_commands(ft.parse_args(["bots", "--slice", "test"]))
    (cmd,) = ft.build_commands(ft.parse_args(["bots", "--slice", "test", "--final-test"]))
    assert cmd[cmd.index("--slice") + 1] == "test"
    (cmd,) = ft.build_commands(ft.parse_args(["bots", "--slice", "train", "--no-kill-switch"]))
    assert "/freqtrade/scripts/bots.py" in cmd and f"/freqtrade/{ft.NO_KILL_DIR}" in cmd
    assert "TrendEma" in cmd and "NostalgiaForInfinityX8" in cmd


def test_ft_bots_train_command():
    (cmd,) = ft.build_commands(ft.parse_args(["bots", "--slice", "train", "--no-kill-switch"]))
    assert "/freqtrade/scripts/bots.py" in cmd and f"/freqtrade/{ft.NO_KILL_DIR}" in cmd


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


def test_half_and_half_is_two_separate_accounts():
    import bots

    idx = pd.date_range("2021-01-01", periods=3, freq="1h", tz="UTC")
    a = pd.Series([1000.0, 2000.0, 2000.0], index=idx)  # doubles
    b = pd.Series([1.0, 1.0, 0.5], index=idx)  # halves
    combo = bots.half_and_half(a, b)
    assert list(combo) == pytest.approx([1.0, 1.5, 1.25])


def test_half_and_half_fills_gaps_with_last_value():
    import bots

    idx = pd.date_range("2021-01-01", periods=4, freq="1h", tz="UTC")
    a = pd.Series([1.0, 1.0, 1.0, 1.0], index=idx)
    b = pd.Series([1.0, 2.0], index=idx[[0, 2]])
    assert list(bots.half_and_half(a, b)) == pytest.approx([1.0, 1.0, 1.5, 1.5])


def test_format_years_lists_every_bot_and_year():
    import bots

    idx = pd.date_range("2021-12-31", periods=48, freq="1h", tz="UTC")
    r = bots.with_years(pd.Series(np.linspace(1, 2, 48), index=idx), 3)
    text = bots.format_years([("A", r), ("B", {"years": {}})])
    assert "2021" in text and "2022" in text and text.count("\n") == 3


# --- safer DCA bot (research row) ------------------------------------------------


def _hourly(close, start="2024-01-01"):
    close = np.asarray(close, dtype=float)
    idx = pd.date_range(start, periods=len(close), freq="1h", tz="UTC")
    return pd.DataFrame({"high": close, "low": close, "close": close}, index=idx)


def test_safe_dca_closed_gate_never_trades():
    c = _hourly(np.linspace(100, 120, 200))
    eq, deals = dcabot.simulate_pair_safe(c, 1.0, fee=0.0, gate=np.zeros(200, dtype=bool))
    assert deals == 0 and (eq == 1.0).all()


def test_safe_dca_open_gate_matches_plain_bot_without_big_fall():
    c = _hourly(100 + 3 * np.sin(np.arange(500) / 5))  # never falls 8% below what was spent
    plain, n1 = dcabot.simulate_pair(c, 1.0, fee=0.001)
    safe, n2 = dcabot.simulate_pair_safe(c, 1.0, fee=0.001)
    assert n1 == n2 and np.allclose(plain.to_numpy(), safe.to_numpy())


def test_safe_dca_stop_caps_a_deal_at_8_percent():
    c = _hourly(np.concatenate([np.full(5, 100.0), np.linspace(100, 40, 200)]))  # long crash
    plain, _ = dcabot.simulate_pair(c, 1.0, fee=0.0)
    safe, deals = dcabot.simulate_pair_safe(c, 1.0, fee=0.0, gate=np.r_[True, np.zeros(204, dtype=bool)])
    assert deals == 1  # stopped once, then the closed gate keeps it out
    lost_fraction_of_spent = 1 - safe.iloc[-1]  # only part of the cash was ever spent
    assert safe.iloc[-1] > plain.iloc[-1]
    assert lost_fraction_of_spent < 0.08 + 1e-9


def test_btc_gate_uses_only_completed_days():
    days = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=160, freq="1D", tz="UTC"),
                         "close": np.concatenate([np.linspace(100, 200, 100), np.linspace(200, 50, 60)])})
    s = days["close"].rolling(50).mean()
    flip = int(np.flatnonzero(~(s > s.shift(10)).to_numpy() & (np.arange(160) > 100))[0])
    flip_day = days["date"].iloc[flip]
    idx = pd.date_range(flip_day - pd.Timedelta(hours=2), periods=30, freq="1h", tz="UTC")
    g = dcabot.btc_gate(idx, days)
    assert g[idx < flip_day + pd.Timedelta(days=1)].all()
    assert not g[idx >= flip_day + pd.Timedelta(days=1)].any()
    # changing the future must not change today's gate
    later = days.copy()
    later.loc[flip + 1 :, "close"] = 1000.0
    assert (dcabot.btc_gate(idx, later)[idx < flip_day + pd.Timedelta(days=1)] == g[idx < flip_day + pd.Timedelta(days=1)]).all()


def test_btc_gate_same_semantics_as_regime_strategy():
    pytest.importorskip("freqtrade")
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "user_data" / "strategies"))
    import regime

    days = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=160, freq="1D", tz="UTC"),
                         "close": np.concatenate([np.linspace(100, 200, 100), np.linspace(200, 50, 60)])})
    hourly = pd.DataFrame({"date": pd.date_range("2024-02-01", periods=24 * 100, freq="1h", tz="UTC")})
    a = dcabot.btc_gate(pd.DatetimeIndex(hourly["date"]), days)
    b = regime.attach_btc_rising(hourly, days).to_numpy()
    assert (a == b).all()


def test_equal_mix_three_accounts_and_half_and_half_unchanged():
    pytest.importorskip("freqtrade")
    import bots

    idx = pd.date_range("2024-01-01", periods=3, freq="1h", tz="UTC")
    a = pd.Series([1.0, 2.0, 3.0], index=idx)   # triples
    b = pd.Series([10.0, 10.0, 10.0], index=idx)  # flat
    c = pd.Series([4.0, 2.0, 0.0], index=idx)    # goes to zero
    mix = bots.equal_mix(a, b, c)
    assert list(mix) == pytest.approx([1.0, (2 + 1 + 0.5) / 3, (3 + 1 + 0) / 3])
    assert list(bots.half_and_half(a, b)) == pytest.approx(list(bots.equal_mix(a, b)))
    assert list(bots.half_and_half(a, b)) == pytest.approx([1.0, 1.5, 2.0])
