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


def test_derisk_hysteresis():
    assert not sizing.derisk_active(1000, [])
    assert not sizing.derisk_active(1000, [-90])  # 9% down: off
    assert sizing.derisk_active(1000, [-110])  # 11% down: on
    assert sizing.derisk_active(1000, [-110, +40])  # 7% down: still on (needs <= 5%)
    assert not sizing.derisk_active(1000, [-110, +70])  # 4% down: off again
    assert sizing.derisk_active(1000, [+200, -150])  # peak 1200, 12.5% down: on


def test_derisk_halves_only(monkeypatch):
    class _T:
        def __init__(self, p, d):
            self.close_profit_abs, self.close_date_utc = p, d

    class _W(_Wallets):
        def get_starting_balance(self):
            return 1000.0

    s = sizing.TrendEmaVolTargetDerisk({})
    s.wallets, s.dp = _W(), _Dp(0.3)
    monkeypatch.setattr(sizing.Trade, "get_trades_proxy", staticmethod(lambda **kw: []))
    assert s.custom_stake_amount("X", None, 1, 0, None, 10_000, 1, None, "long") == pytest.approx(125)
    monkeypatch.setattr(sizing.Trade, "get_trades_proxy", staticmethod(lambda **kw: [_T(-110, 1)]))
    assert s.custom_stake_amount("X", None, 1, 0, None, 10_000, 1, None, "long") == pytest.approx(62.5)
    assert sizing.TrendEmaVolTargetDerisk.confirm_trade_entry is trend_ema.TrendEma.confirm_trade_entry


def test_atr_stop_distance_is_clipped():
    assert sizing.atr_stop_distance(100, 1.0) == pytest.approx(0.03)  # 3% floor
    assert sizing.atr_stop_distance(100, 2.0) == pytest.approx(0.06)
    assert sizing.atr_stop_distance(100, 5.0) == pytest.approx(0.08)  # 8% cap
    assert sizing.atr_stop_distance(100, float("nan")) == pytest.approx(0.08)


def test_atr_stop_stake_keeps_1pct_risk():
    class _DpAtr:
        def get_analyzed_dataframe(self, pair, tf):
            return pd.DataFrame({"date": [pd.Timestamp("2024-01-01", tz="UTC")], "close": [100.0],
                                 "atr": [1.5], "rvol": [0.3]}), None

    s = sizing.TrendEmaVolTargetAtrStop({})
    s.wallets, s.dp = _Wallets(), _DpAtr()
    stake = s.custom_stake_amount("X", None, 1, 0, None, 10_000, 1, None, "long")
    # stop 4.5% -> 1000 x 1% / 4.5% = 222.2 (cap 250), calm coin -> scale 1
    assert stake == pytest.approx(1000 * 0.01 / 0.045)
    assert stake * 0.045 == pytest.approx(10.0)  # a stop-out costs 1% of capital
    cls = sizing.TrendEmaVolTargetAtrStop
    assert cls.stoploss == trend_ema.STOPLOSS and cls.confirm_trade_entry is trend_ema.TrendEma.confirm_trade_entry
    assert cls.populate_entry_trend is trend_ema.TrendEma.populate_entry_trend


def test_breadth_count_and_gate():
    idx = pd.date_range("2024-01-01", periods=600, freq="1h", tz="UTC")
    up = pd.DataFrame({"date": idx, "close": np.linspace(100, 200, 600)})
    down = pd.DataFrame({"date": idx, "close": np.linspace(200, 100, 600)})
    b = sizing.breadth_count({"A": up, "B": up, "C": down, "D": down, "E": down})
    assert b.iloc[-1] == 2  # 2 of 5 above EMA200 -> gate closed
    b3 = sizing.breadth_count({"A": up, "B": up, "C": up, "D": down, "E": down})
    assert b3.iloc[-1] == 3
    cls = sizing.TrendEmaVolTargetBreadth
    assert sizing.BREADTH_MIN_UP == 3 and sizing.BREADTH_SET_SIZE == 5
    assert cls.populate_exit_trend is trend_ema.TrendEma.populate_exit_trend
    assert cls.custom_stake_amount is sizing.TrendEmaVolTarget.custom_stake_amount


def test_vt_neighbours_change_one_thing_and_lens_matches_base():
    base = sizing.TrendEmaVolTarget
    close = np.linspace(100, 200, 1500)
    df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=1500, freq="1h", tz="UTC"),
                       "open": close, "high": close, "low": close, "close": close, "volume": 100.0})
    a = base({}).populate_indicators(df.copy(), {"pair": "X"})
    b = sizing._VolTargetLens({}).populate_indicators(df.copy(), {"pair": "X"})
    for col in ("ema_fast", "ema_slow", "ema_trend", "rvol"):
        assert np.allclose(a[col].fillna(0), b[col].fillna(0))
    assert len(sizing.VT_NEIGHBOURS) == 10
    assert sizing.VTStop6.stoploss == -0.06 and sizing.VTVol480.vol_window == 480
    assert base.stoploss == trend_ema.STOPLOSS  # the live rule is untouched


class _DpBull:
    def __init__(self, vol, bull):
        self.vol, self.bull = vol, bull

    def get_analyzed_dataframe(self, pair, timeframe):
        return pd.DataFrame({"rvol": [self.vol], "btc_bull": [self.bull]}), None


@pytest.mark.parametrize("vol,bull,expected", [(1.6, True, 125 * 0.80 / 1.6), (1.6, False, 125 * 0.60 / 1.6),
                                               (0.5, True, 125.0)])  # fmt: skip
def test_bullvol_stake_uses_80_only_in_bull_and_never_exceeds_base(vol, bull, expected):
    s = sizing.TrendEmaVolTargetBullVol({})
    s.wallets, s.dp = _Wallets(), _DpBull(vol, bull)
    assert s.custom_stake_amount("X", None, 1, 0, None, 10_000, 1, None, "long") == pytest.approx(expected)
    assert sizing.TrendEmaVolTargetBullVol.populate_entry_trend is trend_ema.TrendEma.populate_entry_trend


def test_btc_bull_flags_match_regimes_label_and_use_closed_days():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import regimes

    days = pd.date_range("2020-01-01", periods=800, freq="1D", tz="UTC")
    close = pd.Series(np.concatenate([np.linspace(100, 300, 400), np.linspace(300, 100, 400)]), index=days)
    daily = pd.DataFrame({"date": days, "close": close.to_numpy()})
    hours = pd.Series(pd.date_range("2020-01-02", periods=799 * 24, freq="1h", tz="UTC"))
    flags = sizing.btc_bull_flags(daily, hours)
    lab = regimes.hourly_labels(regimes.label_days(close), pd.DatetimeIndex(hours))["trend"]
    known = lab.notna().to_numpy()
    assert known.sum() > 1000 and (flags[known] == (lab[known] == "bull").to_numpy()).all()
    assert not flags[~known].any()  # before the label exists: treated as not bull (60%)


def test_kama_equals_talib():
    talib = pytest.importorskip("talib")
    rng = np.random.default_rng(1)
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 2000))))
    ours = sizing.kama(close)
    theirs = talib.KAMA(close.to_numpy(), timeperiod=10)
    assert np.isnan(ours.iloc[:9]).all() and ours.iloc[9] == close.iloc[9]
    np.testing.assert_allclose(ours.iloc[10:], theirs[10:], rtol=1e-10)


def test_kama_slows_down_in_chop_and_follows_a_trend():
    chop = pd.Series(np.tile([100.0, 102.0], 100))  # back and forth: ER = 0
    trend = pd.Series(np.linspace(100, 200, 200))  # straight line: ER = 1
    assert abs(sizing.kama(chop).iloc[-1] - sizing.kama(chop).iloc[20]) < 0.5  # barely moves
    assert sizing.kama(trend).iloc[-1] > 199  # hugs the price


def test_kama_strategy_only_swaps_the_fast_line():
    cls = sizing.TrendEmaVolTargetKama
    assert cls.populate_entry_trend is trend_ema.TrendEma.populate_entry_trend
    assert cls.populate_exit_trend is trend_ema.TrendEma.populate_exit_trend
    assert cls.custom_stake_amount is sizing.TrendEmaVolTarget.custom_stake_amount
    rng = np.random.default_rng(4)
    df = pd.DataFrame({"close": 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, 1500))), "volume": 1.0})
    out = cls({}).populate_indicators(df.copy(), {})
    assert np.allclose(out["ema_fast"].iloc[20:], sizing.kama(df["close"]).iloc[20:])
    s = cls({})
    entries = s.populate_entry_trend(out.copy(), {})["enter_long"].fillna(0).sum()
    assert entries > 5


def test_daily_rule_entry_is_the_false_to_true_switch_and_exit_is_the_cross_down():
    cls = sizing.TrendEmaVolTargetDaily
    assert cls.timeframe == "1d" and cls.stoploss == trend_ema.STOPLOSS and cls.vol_window == 30
    assert cls.custom_stake_amount is sizing.TrendEmaVolTarget.custom_stake_amount  # VolTarget sizing, R2/R4
    close = np.r_[np.linspace(100, 80, 80), np.linspace(80, 130, 60), np.linspace(130, 90, 60)]
    df = pd.DataFrame({"close": close, "volume": 1.0})
    s = cls({})
    d = s.populate_exit_trend(s.populate_entry_trend(s.populate_indicators(df.copy(), {}), {}), {})
    ok = (d["ema_fast"] > d["ema_slow"]) & (d["close"] > d["ema_slow"])
    entries = d.index[d["enter_long"] == 1].tolist()
    assert entries and all(ok[i] and not ok[i - 1] for i in entries)  # only on the switch day
    exits = d.index[d["exit_long"] == 1].tolist()
    assert exits and all(d["ema_fast"][i] < d["ema_slow"][i] and d["ema_fast"][i - 1] >= d["ema_slow"][i - 1] for i in exits)
    assert np.isclose(d["rvol"].iloc[-1], np.log(df["close"]).diff().iloc[-30:].std() * np.sqrt(365))


def test_window24_only_with_alt2024b():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import ft

    with pytest.raises(SystemExit, match="window24"):
        ft.build_commands(ft.parse_args(["backtest", "--slice", "window24", "--strategy", "TrendEma"]))
    cmd = ft.build_commands(ft.parse_args(["backtest", "--slice", "window24", "--universe", "alt2024b", "--strategy", "TrendEmaVolTargetDaily"]))[0]
    assert "20240101-20250807" in cmd and "1d" in cmd


def test_fee_aware_filter_blocks_entries_with_a_small_hourly_move():
    cls = sizing.TrendEmaVolTargetFeeAware
    assert sizing.FEE_COVER * sizing.ROUND_TRIP_COST == pytest.approx(0.009)
    assert cls.populate_exit_trend is trend_ema.TrendEma.populate_exit_trend
    assert cls.custom_stake_amount is sizing.TrendEmaVolTarget.custom_stake_amount
    rng = np.random.default_rng(3)
    for sigma, expect_entries in ((0.002, False), (0.02, True)):  # calm coin: ATR% ~0.2%; wild: ~2%
        close = 100 * np.exp(np.cumsum(rng.normal(0.0003, sigma, 3000)))
        df = pd.DataFrame({"close": close, "high": close * (1 + sigma), "low": close * (1 - sigma), "volume": 1.0})
        base = sizing.TrendEmaVolTarget({})
        b = base.populate_entry_trend(base.populate_indicators(df.copy(), {}), {})
        s = cls({})
        f = s.populate_entry_trend(s.populate_indicators(df.copy(), {}), {})
        kept = f["enter_long"].fillna(0) == 1
        assert (b["enter_long"].fillna(0)[kept] == 1).all()  # only ever removes entries
        assert (f.loc[kept, "atr_pct"] >= 0.009).all()
        assert kept.any() == expect_entries
