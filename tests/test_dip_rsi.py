"""Tests for the RSI(2) dip-buying strategy (Phase 2, mean reversion)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("freqtrade")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "user_data" / "strategies"))
import dip_rsi  # noqa: E402
import trend_ema  # noqa: E402


def candles(close, freq="1h"):
    close = np.asarray(close, dtype=float)
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=len(close), freq=freq, tz="UTC"),
            "open": close,
            "high": close * 1.001,
            "low": close * 0.999,
            "close": close,
            "volume": np.full(len(close), 100.0),
        }
    )


def test_rsi_only_rises_is_100_only_falls_is_0():
    assert dip_rsi.rsi(pd.Series(np.arange(1.0, 50.0)), 2).iloc[-1] == pytest.approx(100.0)
    assert dip_rsi.rsi(pd.Series(np.arange(50.0, 1.0, -1)), 2).iloc[-1] == pytest.approx(0.0)


def test_rsi_first_value_is_empty_not_a_fake_number():
    assert np.isnan(dip_rsi.rsi(pd.Series([1.0, 2.0, 3.0]), 2).iloc[0])


def test_rsi_stays_between_0_and_100():
    rng = np.random.default_rng(1)
    values = dip_rsi.rsi(pd.Series(100 + rng.normal(0, 1, 500).cumsum()), 2).dropna()
    assert values.between(0, 100).all()


def test_dip_stop_price_uses_atr_but_never_wider_than_8_percent():
    assert dip_rsi.dip_stop_price(100, 2, 2.5, 0.08) == pytest.approx(95.0)
    assert dip_rsi.dip_stop_price(100, 10, 2.5, 0.08) == pytest.approx(92.0)


def uptrend_with_dip():
    # long steady rise (trend up), then 3 sharp red candles, then a bounce
    rise = np.linspace(100, 200, 600)
    dip = [198, 195, 192]
    bounce = [196, 199, 202]
    return candles(np.concatenate([rise, dip, bounce]))


def test_buys_the_dip_in_an_uptrend_and_sells_the_bounce():
    strat = dip_rsi.DipRsi({})
    df = strat.populate_indicators(uptrend_with_dip(), {"pair": "BTC/USDT"})
    df = strat.populate_entry_trend(df, {"pair": "BTC/USDT"})
    df = strat.populate_exit_trend(df, {"pair": "BTC/USDT"})
    entries = df.index[df["enter_long"] == 1].tolist()
    assert entries and min(entries) >= 600  # only on the dip, never during the smooth rise
    assert (df["exit_long"].iloc[-3:] == 1).any()  # bounce above SMA5 -> sell


def test_no_dip_buying_in_a_downtrend():
    fall = np.linspace(200, 100, 600)
    df = candles(np.concatenate([fall, [97, 94, 91]]))
    strat = dip_rsi.DipRsi({})
    df = strat.populate_indicators(df, {"pair": "BTC/USDT"})
    df = strat.populate_entry_trend(df, {"pair": "BTC/USDT"})
    assert df.get("enter_long", pd.Series(dtype=float)).fillna(0).sum() == 0


def test_risk_rules_are_the_live_ones():
    for cls in (dip_rsi.DipRsi, dip_rsi.DipRsi4h):
        assert cls.stoploss == trend_ema.STOPLOSS
        assert cls.can_short is False
        assert issubclass(cls, trend_ema.TrendEma)  # kill switch + 1% sizing inherited
    assert dip_rsi.DipRsi4h.timeframe == "4h"
    assert dip_rsi.DipRsi.timeframe == "1h"


def test_indicators_use_only_past_candles():
    # changing the last candle must not change any earlier indicator value
    df = uptrend_with_dip()
    strat = dip_rsi.DipRsi({})
    a = strat.populate_indicators(df.copy(), {"pair": "X"})
    df2 = df.copy()
    df2.loc[df2.index[-1], ["close", "high", "low", "open"]] = 999.0
    b = strat.populate_indicators(df2, {"pair": "X"})
    cols = ["ema_trend", "rsi", "sma_exit", "atr"]
    pd.testing.assert_frame_equal(a[cols].iloc[:-1], b[cols].iloc[:-1])
