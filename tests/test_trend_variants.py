"""Tests for the experimental TrendEma variants."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("freqtrade")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "user_data" / "strategies"))
import trend_ema  # noqa: E402
import trend_variants as tv  # noqa: E402

VARIANTS = [tv.TrendEmaAtr, tv.TrendEmaAtrTrail, tv.TrendEma4h, tv.TrendBreakout]


def candles(close, high=None, low=None):
    close = np.asarray(close, dtype=float)
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=len(close), freq="1h", tz="UTC"),
            "open": close,
            "high": close if high is None else np.asarray(high, dtype=float),
            "low": close if low is None else np.asarray(low, dtype=float),
            "close": close,
            "volume": np.full(len(close), 100.0),
        }
    )


def test_atr_of_constant_range_is_that_range():
    # every candle moves exactly 2 (high-low), close never jumps -> ATR = 2
    df = candles([100] * 100, high=[101] * 100, low=[99] * 100)
    assert tv.atr(df).iloc[-1] == pytest.approx(2.0)


def test_atr_counts_gaps_from_previous_close():
    # flat candles, but price jumps 10 between candles -> true range 10
    close = [100, 110] * 50
    df = candles(close)
    assert tv.atr(df).iloc[-1] == pytest.approx(10.0, rel=0.05)


def test_atr_stop_distance_capped_at_8_percent():
    assert tv.atr_stop_distance(100, 1, 2.5, 0.08) == pytest.approx(0.025)
    assert tv.atr_stop_distance(100, 10, 2.5, 0.08) == pytest.approx(0.08)


def test_breakout_uses_only_previous_candles():
    # rises to 120, then on candle 450 jumps above the old high
    close = np.concatenate([np.linspace(100, 120, 450), [125]])
    df = candles(close)
    strat = tv.TrendBreakout({})
    df = strat.populate_indicators(df, {"pair": "BTC/USDT"})
    # high_n at the last candle must not include the last candle itself
    assert df["high_n"].iloc[-1] == pytest.approx(120.0)
    df = strat.populate_entry_trend(df, {"pair": "BTC/USDT"})
    assert df["enter_long"].iloc[-1] == 1


def test_trail_variant_has_no_exit_signal():
    assert tv.TrendEmaAtrTrail.use_exit_signal is False
    assert tv.TrendEmaAtr.use_exit_signal is True


@pytest.mark.parametrize("cls", VARIANTS, ids=lambda c: c.__name__)
def test_variants_keep_risk_rules(cls):
    assert cls.stoploss == trend_ema.STOPLOSS
    assert cls.can_short is False
    methods = [p["method"] for p in cls({}).protections]
    assert "StoplossGuard" in methods
    # kill switch lives in confirm_trade_entry; variants must not override it
    assert cls.confirm_trade_entry is trend_ema.TrendEma.confirm_trade_entry
