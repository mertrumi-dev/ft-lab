"""Tests for the daily 200-day SMA rule."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

import pytest

pytest.importorskip("freqtrade")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "user_data" / "strategies"))
import sma_daily  # noqa: E402
import trend_ema  # noqa: E402


def daily(close):
    close = np.asarray(close, dtype=float)
    return pd.DataFrame({
        "date": pd.date_range("2021-01-01", periods=len(close), freq="1D", tz="UTC"),
        "open": close, "high": close, "low": close, "close": close, "volume": 1.0,
    })  # fmt: skip


def run(close):
    s = sma_daily.TrendSmaDaily({})
    df = s.populate_indicators(daily(close), {"pair": "BTC/USDT"})
    return s.populate_exit_trend(s.populate_entry_trend(df, {}), {})


def test_no_signal_before_200_days():
    df = run(np.linspace(100, 200, 199))
    assert df.get("enter_long", pd.Series(0, index=df.index)).fillna(0).sum() == 0


def test_in_above_out_below():
    close = list(np.full(200, 100.0)) + [110.0, 90.0]  # SMA ~100
    df = run(close)
    assert df["enter_long"].iloc[-2] == 1 and df["exit_long"].iloc[-1] == 1
    assert df["enter_long"].fillna(0).iloc[-1] == 0


def test_daily_timeframe_and_live_risk_rules():
    s = sma_daily.TrendSmaDaily
    assert s.timeframe == "1d"
    assert s.stoploss == trend_ema.STOPLOSS and s.can_short is False
    assert issubclass(s, trend_ema.TrendEma)  # 1% sizing + kill switch inherited


def test_protections_are_short_on_daily_candles():
    p = sma_daily.TrendSmaDaily({}).protections
    assert all(x["stop_duration_candles"] <= 1 for x in p)
