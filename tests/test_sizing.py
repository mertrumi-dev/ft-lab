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


@pytest.mark.parametrize("cls,target", [(sizing.VolTarget45, 0.45), (sizing.VolTarget80, 0.80)])
def test_neighbours_only_move_the_target(cls, target):
    s = cls({})
    s.wallets, s.dp = _Wallets(), _Dp(1.6)
    assert s.custom_stake_amount("X", None, 1, 0, None, 10_000, 1, None, "long") == pytest.approx(125 * target / 1.6)
    assert cls.populate_entry_trend is trend_ema.TrendEma.populate_entry_trend


def test_voltarget_btc_combines_exactly_two_parents():
    import regime

    cls = sizing.TrendEmaVolTargetBtc
    assert cls.populate_entry_trend is regime.TrendEmaBtcRising.populate_entry_trend
    assert cls.custom_stake_amount is sizing.TrendEmaVolTarget.custom_stake_amount
    assert cls.informative_pairs is regime.TrendEmaBtcRising.informative_pairs
    assert cls.startup_candle_count >= sizing.VOL_WINDOW
    assert cls.confirm_trade_entry is trend_ema.TrendEma.confirm_trade_entry
    # both indicator steps run (BtcRising -> VolTarget -> TrendEma)
    close = np.linspace(100, 200, 1500)
    df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=1500, freq="1h", tz="UTC"),
                       "open": close, "high": close, "low": close, "close": close, "volume": 100.0})
    out = cls({}).populate_indicators(df, {"pair": "X"})
    assert {"btc_rising", "rvol", "ema_trend"} <= set(out.columns)


def test_portfolio_room():
    assert sizing.portfolio_room([]) == pytest.approx(0.15)
    assert sizing.portfolio_room([0.075, 0.05]) == pytest.approx(0.025)
    assert sizing.portfolio_room([0.1, 0.1]) == 0.0


def test_portfolio_shrinks_or_blocks_never_grows(monkeypatch):
    class _T:
        def __init__(self, pair, stake):
            self.pair, self.stake_amount = pair, stake

    s = sizing.TrendEmaVolTargetPortfolio({})
    s.wallets, s.dp = _Wallets(), _Dp(0.6)  # every coin 60% vol -> VolTarget stake 125
    monkeypatch.setattr(sizing.Trade, "get_trades_proxy", staticmethod(lambda **kw: []))
    assert s.custom_stake_amount("X", None, 1, 0, None, 10_000, 1, None, "long") == pytest.approx(125)
    # two full trades open: load 2 x 0.125 x 0.6 = 0.15 -> no room
    monkeypatch.setattr(sizing.Trade, "get_trades_proxy", staticmethod(lambda **kw: [_T("A", 125), _T("B", 125)]))
    assert s.custom_stake_amount("X", None, 1, 0, None, 10_000, 1, None, "long") == pytest.approx(0)
    # one trade open: load 0.075 -> room 0.075 -> 0.075/0.6 = 12.5% = 125, same as VolTarget
    monkeypatch.setattr(sizing.Trade, "get_trades_proxy", staticmethod(lambda **kw: [_T("A", 125)]))
    assert s.custom_stake_amount("X", None, 1, 0, None, 10_000, 1, None, "long") == pytest.approx(125)
    assert sizing.TrendEmaVolTargetPortfolio.confirm_trade_entry is trend_ema.TrendEma.confirm_trade_entry


def test_daily_above_sma_uses_completed_days_only():
    days = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=260, freq="1D", tz="UTC"),
                         "close": np.concatenate([np.full(220, 100.0), np.full(40, 200.0)])})
    jump = days["date"].iloc[220]  # first day closing at 200 (> SMA200)
    hours = pd.Series(pd.date_range(jump - pd.Timedelta(hours=3), periods=30, freq="1h", tz="UTC"))
    flags = sizing.daily_above_sma(days, hours)
    assert not flags[(hours < jump + pd.Timedelta(days=1)).to_numpy()].any()
    assert flags[(hours >= jump + pd.Timedelta(days=1)).to_numpy()].all()


def test_pool2_core_pairs_always_allowed_and_signals_unchanged():
    cls = sizing.TrendEmaVolTargetPool2
    assert cls.top_n == 20 and set(sizing.CORE_PAIRS) == {"BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"}
    assert cls.custom_stake_amount is sizing.TrendEmaVolTarget.custom_stake_amount
    assert cls.confirm_trade_entry is trend_ema.TrendEma.confirm_trade_entry
    close = np.linspace(100, 200, 1500)
    df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=1500, freq="1h", tz="UTC"),
                       "open": close, "high": close, "low": close, "close": close, "volume": 100.0})
    out = cls({}).populate_indicators(df, {"pair": "BTC/USDT"})
    assert out["in_top"].all()


def _frame(close, low=None):
    close = np.asarray(close, dtype=float)
    df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=len(close), freq="1h", tz="UTC"),
                       "open": close, "high": close, "low": close if low is None else np.asarray(low, float),
                       "close": close, "volume": 100.0})
    return trend_ema.TrendEma({}).populate_indicators(df, {"pair": "X"})


def test_pullback_buys_first_touch_after_arming_only():
    close = np.concatenate([np.linspace(100, 200, 600), np.linspace(200, 185, 60), np.linspace(185, 260, 340)])
    df = _frame(close)
    base = trend_ema.TrendEma({}).populate_entry_trend(df.copy(), {})
    arm = int(base.index[base["enter_long"] == 1][0])
    low = close.copy()
    low[arm + 5] = df["ema_fast"].iloc[arm + 5] * 0.999  # one dip to EMA20, 5 candles later
    low[arm + 7] = df["ema_fast"].iloc[arm + 7] * 0.999  # a second dip: must NOT buy again
    out = sizing.pullback_entries(_frame(close, low))
    hits = list(out.index[out])
    assert arm + 5 in hits and arm + 7 not in hits and arm not in hits


def test_pullback_skips_without_touch_in_window():
    close = np.concatenate([np.linspace(100, 200, 600), np.linspace(200, 185, 60), np.linspace(185, 260, 340)])
    df = _frame(close)
    base = trend_ema.TrendEma({}).populate_entry_trend(df.copy(), {})
    arm = int(base.index[base["enter_long"] == 1][0])
    low = close.copy()
    low[arm + 13] = df["ema_fast"].iloc[arm + 13] * 0.999  # touch too late (13 > 12)
    out = sizing.pullback_entries(_frame(close, low))
    assert not out.iloc[arm : arm + 14].any()


def test_pullback_keeps_exit_stop_and_size():
    cls = sizing.TrendEmaVolTargetPullback
    assert cls.populate_exit_trend is trend_ema.TrendEma.populate_exit_trend
    assert cls.custom_stake_amount is sizing.TrendEmaVolTarget.custom_stake_amount
    assert cls.stoploss == trend_ema.STOPLOSS and cls.confirm_trade_entry is trend_ema.TrendEma.confirm_trade_entry


def test_voltarget_2h_same_rule_scaled_vol():
    cls = sizing.TrendEmaVolTarget2h
    assert cls.timeframe == "2h" and cls.vol_window == 360 and cls.periods_per_year == 4380
    assert cls.populate_entry_trend is trend_ema.TrendEma.populate_entry_trend
    assert cls.custom_stake_amount is sizing.TrendEmaVolTarget.custom_stake_amount
    rng = np.random.default_rng(1)
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.6 / np.sqrt(4380), 3000))))
    assert sizing.realized_vol(close, 360, 4380).iloc[-1] == pytest.approx(0.6, rel=0.15)
