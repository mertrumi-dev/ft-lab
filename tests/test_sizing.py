"""Tests for round 15: TrendEmaVolTarget (volatility-scaled position size)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("freqtrade")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "user_data" / "strategies"))
import sizing  # noqa: E402
import trend_ema  # noqa: E402


def test_scale_never_grows_the_stake():
    assert sizing.vol_scale(0.30) == 1.0  # calm coin: normal stake, never more
    assert sizing.vol_scale(1.20) == pytest.approx(0.5)
    assert sizing.vol_scale(float("nan")) == 1.0
    assert sizing.vol_scale(0.0) == 1.0


def test_realized_vol_of_known_series():
    rng = np.random.default_rng(0)
    hourly_sd = 0.6 / np.sqrt(sizing.HOURS_PER_YEAR)  # 60% a year
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, hourly_sd, 5000))))
    assert sizing.realized_vol(close).iloc[-1] == pytest.approx(0.6, rel=0.1)


def test_realized_vol_uses_only_the_past():
    close = pd.Series(np.linspace(100, 200, 2000))
    a = sizing.realized_vol(close)
    b = sizing.realized_vol(pd.concat([close.iloc[:1500], pd.Series(np.full(500, 5.0))], ignore_index=True))
    assert a.iloc[:1500].equals(b.iloc[:1500])


class _Wallets:
    def get_total_stake_amount(self):
        return 1000.0


class _Dp:
    def __init__(self, vol):
        self.vol = vol

    def get_analyzed_dataframe(self, pair, timeframe):
        return pd.DataFrame({"rvol": [self.vol]}), None


@pytest.mark.parametrize("vol,expected", [(0.3, 125.0), (1.2, 62.5), (2.4, 31.25)])
def test_stake(vol, expected):
    s = sizing.TrendEmaVolTarget({})
    s.wallets, s.dp = _Wallets(), _Dp(vol)
    assert s.custom_stake_amount("X", None, 1, 0, None, 10_000, 1, None, "long") == pytest.approx(expected)


def test_keeps_risk_rules_and_signals():
    cls = sizing.TrendEmaVolTarget
    assert cls.stoploss == trend_ema.STOPLOSS and cls.can_short is False
    assert cls.confirm_trade_entry is trend_ema.TrendEma.confirm_trade_entry
    assert cls.populate_entry_trend is trend_ema.TrendEma.populate_entry_trend
    assert cls.populate_exit_trend is trend_ema.TrendEma.populate_exit_trend
