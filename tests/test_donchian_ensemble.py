"""Tests for TrendDonchianEnsemble (daily channel voting)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("freqtrade")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "user_data" / "strategies"))
import donchian_ensemble as de  # noqa: E402
import trend_ema  # noqa: E402


def test_channel_enters_on_breakout_and_exits_below_rising_middle():
    # flat at 100 (range 99-101), breaks out to 110, then falls back to 95
    close = np.array([100.0] * 10 + [110, 112, 114, 108, 100, 95])
    high, low = close + 1, close - 1
    s = de.channel_state(high, low, close, 5)
    assert s[9] == 0  # no breakout yet
    assert s[10] == 1  # 110 > previous 5-day high 101
    assert s[-1] == 0  # fell below the trailing middle


def test_channel_uses_only_past_candles():
    # today's own high must not count: a candle that is its own high still breaks out
    close = np.array([100.0] * 6 + [105])
    s = de.channel_state(close + 0.5, close - 0.5, close, 5)
    assert s[-1] == 1


def test_stop_never_moves_down():
    close = np.array([100.0] * 6 + [120, 140, 130, 125, 121, 119])
    s = de.channel_state(close + 1, close - 1, close, 5)
    # once the middle rose to ~120, a close at 119 exits even though the channel later drops
    assert s[7] == 1 and s[-1] == 0


def test_target_fraction_votes_times_vol_scaling():
    assert de.target_fraction(0.0, 0.5) == 0.0
    assert de.target_fraction(1.0, 0.25) == pytest.approx(1.0)
    assert de.target_fraction(1.0, 1.0) == pytest.approx(0.25)  # wild coin -> quarter size
    assert de.target_fraction(0.5, 0.1) == pytest.approx(0.5)  # calm coin: never above votes
    assert de.target_fraction(1.0, float("nan")) == 0.0


def test_indicators_and_signals_on_a_trend():
    n = 900
    close = np.concatenate([np.linspace(100, 60, 450), np.linspace(60, 200, 450)])
    df = pd.DataFrame({"date": pd.date_range("2019-01-01", periods=n, freq="1D", tz="UTC"),
                       "open": close, "high": close * 1.001, "low": close * 0.999,
                       "close": close, "volume": 1.0})
    s = de.TrendDonchianEnsemble({})
    df = s.populate_indicators(df, {"pair": "BTC/USDT"})
    df = s.populate_entry_trend(df, {"pair": "BTC/USDT"})
    df = s.populate_exit_trend(df, {"pair": "BTC/USDT"})
    assert df["ensemble"].iloc[440] == 0  # falling: nobody long
    assert df["ensemble"].iloc[-1] == 1  # long rise: all 9 long
    assert (df["target"] <= 1).all() and (df["target"] >= 0).all()
    assert df["enter_long"].fillna(0).iloc[-1] == 1


def test_keeps_risk_rules():
    cls = de.TrendDonchianEnsemble
    assert cls.stoploss == trend_ema.STOPLOSS
    assert cls.can_short is False
    assert cls.confirm_trade_entry is trend_ema.TrendEma.confirm_trade_entry  # kill switch
    assert "StoplossGuard" in [p["method"] for p in cls({}).protections]


def test_budget_never_above_one_percent_risk():
    # budget = capital x 1% / 8% = 12.5%; target <= 1 -> at most 1% of capital lost at the stop
    s = de.TrendDonchianEnsemble({})
    s.wallets = type("W", (), {"get_total_stake_amount": lambda self: 1000.0})()
    assert s._budget() == pytest.approx(125.0)
