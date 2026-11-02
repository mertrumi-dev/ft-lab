"""Tests for round 15: TrendEmaVolTarget (volatility-scaled position size)."""

import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
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


def test_cooldown24_locks_the_pair_for_a_day_after_a_signal_exit_only():
    from datetime import datetime, timedelta, timezone

    s = sizing.TrendEmaVolTargetCooldown24({})
    calls = []
    s.lock_pair = lambda pair, until, reason=None, side="*": calls.append((pair, until, reason))
    now = datetime(2030, 1, 1, 10, tzinfo=timezone.utc)
    assert s.confirm_trade_exit("BTC/USDT", None, "limit", 1.0, 100.0, "GTC", "ema_cross_down", now) is True
    assert calls == [("BTC/USDT", now + timedelta(hours=24), "24 candles after a signal exit")]
    assert s.confirm_trade_exit("ETH/USDT", None, "market", 1.0, 92.0, "GTC", "stop_loss", now) is True
    assert len(calls) == 1  # stop exits: only the normal 2-candle CooldownPeriod
    cls = sizing.TrendEmaVolTargetCooldown24
    assert cls.populate_entry_trend is trend_ema.TrendEma.populate_entry_trend
    assert cls.custom_stake_amount is sizing.TrendEmaVolTarget.custom_stake_amount
    assert cls.protections.fget is trend_ema.TrendEma.protections.fget


@pytest.mark.parametrize("cls,n", [(sizing.VTCooldown12, 12), (sizing.VTCooldown48, 48)])
def test_cooldown_neighbours_only_move_the_length(cls, n):
    from datetime import datetime, timedelta, timezone

    s = cls({})
    calls = []
    s.lock_pair = lambda pair, until, reason=None, side="*": calls.append(until)
    now = datetime(2030, 1, 1, tzinfo=timezone.utc)
    s.confirm_trade_exit("X/USDT", None, "limit", 1.0, 1.0, "GTC", "ema_cross_down", now)
    assert calls == [now + timedelta(hours=n)]
    assert cls.confirm_trade_exit is sizing.TrendEmaVolTargetCooldown24.confirm_trade_exit


def test_derisk2x_sells_half_once_when_the_vol_scale_halves():
    from datetime import datetime, timezone
    from types import SimpleNamespace

    cls = sizing.TrendEmaVolTargetDerisk2x
    assert cls.position_adjustment_enable and cls.max_entry_position_adjustment == 0
    assert cls.custom_stake_amount is sizing.TrendEmaVolTarget.custom_stake_amount
    dates = pd.date_range("2030-01-01", periods=10, freq="1h", tz="UTC")
    calm, wild = 0.5, 1.6  # scale 1.0 at entry; 0.6/1.6 = 0.375 < 0.5 -> derisk
    df = pd.DataFrame({"date": dates, "rvol": [calm] * 5 + [wild] * 5})

    class Dp:
        def get_analyzed_dataframe(self, pair, tf):
            return df, None

    s = cls({})
    s.dp = Dp()
    trade = SimpleNamespace(pair="X/USDT", nr_of_successful_exits=0, has_open_orders=False, stake_amount=100.0,
                            open_date_utc=datetime(2030, 1, 1, 3, tzinfo=timezone.utc))  # fmt: skip
    args = (None, 1.0, 0.0, 5.0, 1000.0, 1.0, 1.0, 0.0, 0.0)
    assert s.adjust_trade_position(trade, *args) == (-50.0, "derisk_vol_2x")
    trade.nr_of_successful_exits = 1
    assert s.adjust_trade_position(trade, *args) is None  # only once
    trade.nr_of_successful_exits = 0
    df.loc[5:, "rvol"] = 0.9  # 0.6/0.9 = 0.67 >= 0.5 x 1.0 -> keep
    assert s.adjust_trade_position(trade, *args) is None


def test_derisk72h_uses_the_short_vol_now_and_the_30d_vol_at_entry():
    from datetime import datetime, timezone
    from types import SimpleNamespace

    cls = sizing.TrendEmaVolTargetDerisk72h
    assert sizing.SHORT_VOL_WINDOW == 72
    dates = pd.date_range("2030-01-01", periods=10, freq="1h", tz="UTC")
    df = pd.DataFrame({"date": dates, "rvol": [0.5] * 10, "rvol_short": [0.5] * 5 + [1.6] * 5})

    class Dp:
        def get_analyzed_dataframe(self, pair, tf):
            return df, None

    s = cls({})
    s.dp = Dp()
    trade = SimpleNamespace(pair="X/USDT", nr_of_successful_exits=0, has_open_orders=False, stake_amount=80.0,
                            open_date_utc=datetime(2030, 1, 1, 3, tzinfo=timezone.utc))  # fmt: skip
    args = (None, 1.0, 0.0, 5.0, 1000.0, 1.0, 1.0, 0.0, 0.0)
    assert s.adjust_trade_position(trade, *args) == (-40.0, "derisk_vol_72h")  # 30d vol calm, 72h vol wild
    rng = np.random.default_rng(2)
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 1500))))
    ind = s.populate_indicators(pd.DataFrame({"close": close, "volume": 1.0}), {})
    assert np.isclose(ind["rvol_short"].iloc[-1], np.log(close).diff().iloc[-72:].std() * np.sqrt(8760))


@pytest.mark.parametrize("cls,w", [(sizing.VTDerisk48h, 48), (sizing.VTDerisk96h, 96)])
def test_derisk_neighbours_only_move_the_short_window(cls, w):
    assert cls.short_vol_window == w and sizing.TrendEmaVolTargetDerisk72h.short_vol_window == 72
    assert cls.adjust_trade_position is sizing.TrendEmaVolTargetDerisk72h.adjust_trade_position
    rng = np.random.default_rng(5)
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 1500))))
    ind = cls({}).populate_indicators(pd.DataFrame({"close": close, "volume": 1.0}), {})
    assert np.isclose(ind["rvol_short"].iloc[-1], np.log(close).diff().iloc[-w:].std() * np.sqrt(8760))


def test_minhold24_refuses_young_signal_exits_and_exits_when_old_and_below():
    from datetime import datetime, timedelta, timezone
    from types import SimpleNamespace

    cls = sizing.TrendEmaVolTargetMinHold24
    assert sizing.MIN_HOLD_CANDLES == 24 and cls.stoploss == trend_ema.STOPLOSS
    s = cls({})
    opened = datetime(2030, 1, 1, tzinfo=timezone.utc)
    trade = SimpleNamespace(open_date_utc=opened)
    young, old = opened + timedelta(hours=23), opened + timedelta(hours=24)
    assert s.confirm_trade_exit("X/USDT", trade, "limit", 1, 1, "GTC", "ema_cross_down", young) is False
    assert s.confirm_trade_exit("X/USDT", trade, "limit", 1, 1, "GTC", "ema_cross_down", old) is True
    assert s.confirm_trade_exit("X/USDT", trade, "market", 1, 1, "GTC", "stop_loss", young) is True  # stop never delayed
    frames = {"below": pd.DataFrame({"ema_fast": [1.0], "ema_slow": [2.0]}), "above": pd.DataFrame({"ema_fast": [3.0], "ema_slow": [2.0]})}

    class Dp:
        state = "below"

        def get_analyzed_dataframe(self, pair, tf):
            return frames[self.state], None

    s.dp = Dp()
    assert s.custom_exit("X/USDT", trade, young, 1.0, 0.0) is None  # too young even if below
    assert s.custom_exit("X/USDT", trade, old, 1.0, 0.0) == "ema_below_after_minhold"
    s.dp.state = "above"
    assert s.custom_exit("X/USDT", trade, old, 1.0, 0.0) is None


def test_momentum_half_flags_rank_top_half_and_positive_only():
    dates = pd.date_range("2030-01-01", periods=6, freq="1h", tz="UTC")
    mk = lambda vals: pd.DataFrame({"date": dates, "close": vals})  # noqa: E731
    frames = {"A": mk([100, 110, 120, 130, 140, 150]), "B": mk([100, 101, 102, 103, 104, 105]),
              "C": mk([100, 99, 98, 97, 96, 95]), "D": mk([100, 100, 100, 100, 100, 100])}  # fmt: skip
    f = sizing.momentum_half_flags(frames, window=2)
    last = f.iloc[-1]
    assert bool(last["A"]) and bool(last["B"])  # top half of 4 = 2, both rising
    assert not bool(last["C"]) and not bool(last["D"])  # bottom half (and not rising)
    assert not f.iloc[:3].any().any()  # no full window yet (2 back + shift 1)
    frames2 = {"A": frames["C"], "B": frames["D"]}
    assert not sizing.momentum_half_flags(frames2, window=2).iloc[-1].any()  # top half but falling/flat -> no
    assert sizing.TrendEmaVolTargetMomHalf.populate_entry_trend is sizing.TrendEmaVolTargetTopVol.populate_entry_trend


def test_adx_gate_only_removes_entries_below_the_threshold():
    from trend_variants import adx

    cls = sizing.TrendEmaVolTargetAdx
    assert cls.adx_min == 20 and sizing.VTAdx15.adx_min == 15 and sizing.VTAdx25.adx_min == 25
    assert cls.custom_stake_amount is sizing.TrendEmaVolTarget.custom_stake_amount
    rng = np.random.default_rng(9)
    close = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, 3000)))
    df = pd.DataFrame({"close": close, "high": close * 1.004, "low": close * 0.996, "volume": 1.0})
    base = sizing.TrendEmaVolTarget({})
    b = base.populate_entry_trend(base.populate_indicators(df.copy(), {}), {})
    s = cls({})
    f = s.populate_entry_trend(s.populate_indicators(df.copy(), {}), {})
    kept, removed = f["enter_long"].fillna(0) == 1, (b["enter_long"].fillna(0) == 1) & (f["enter_long"].fillna(0) != 1)
    assert (b["enter_long"].fillna(0)[kept] == 1).all() and (f.loc[kept, "adx"] > 20).all()
    assert (f.loc[removed, "adx"] <= 20).all() and kept.any() and removed.any()
    assert np.allclose(f["adx"].dropna(), adx(df).loc[f["adx"].dropna().index])


def test_take_half_2r_sells_half_once_at_plus_16_percent():
    from types import SimpleNamespace

    cls = sizing.TrendEmaVolTargetTakeHalf2R
    assert cls.position_adjustment_enable and cls.max_entry_position_adjustment == 0
    assert sizing.TAKE_PROFIT_R * abs(cls.stoploss) == pytest.approx(0.16)
    assert cls.populate_exit_trend is trend_ema.TrendEma.populate_exit_trend
    assert cls.custom_stake_amount is sizing.TrendEmaVolTarget.custom_stake_amount
    s = cls({})
    trade = SimpleNamespace(nr_of_successful_exits=0, has_open_orders=False, stake_amount=120.0)
    call = lambda profit: s.adjust_trade_position(trade, None, 1.0, profit, 5.0, 1000.0, 1.0, 1.0, profit, profit)  # noqa: E731
    assert call(0.159) is None
    assert call(0.16) == (-60.0, "take_half_2r") and call(0.30) == (-60.0, "take_half_2r")
    trade.nr_of_successful_exits = 1
    assert call(0.30) is None  # only once
    trade.nr_of_successful_exits, trade.has_open_orders = 0, True
    assert call(0.30) is None  # not while an order is still open


def test_lowcorr_refuses_a_coin_too_correlated_with_an_open_one(monkeypatch):
    from datetime import datetime, timezone
    from types import SimpleNamespace

    rng = np.random.default_rng(1)
    dates = pd.date_range("2030-01-01", periods=800, freq="1h", tz="UTC")
    base = rng.normal(0, 0.01, 800)
    mk = lambda r: pd.DataFrame({"date": dates, "close": 100 * np.exp(np.cumsum(r))})  # noqa: E731
    frames = {"A/USDT": mk(base), "TWIN/USDT": mk(base + rng.normal(0, 0.002, 800)), "OTHER/USDT": mk(rng.normal(0, 0.01, 800))}
    assert sizing.return_correlation(frames["A/USDT"], frames["TWIN/USDT"]) > 0.95
    assert abs(sizing.return_correlation(frames["A/USDT"], frames["OTHER/USDT"])) < 0.2

    class Dp:
        runmode = SimpleNamespace(value="backtest")

        def get_analyzed_dataframe(self, pair, tf):
            return frames[pair], None

    s = sizing.TrendEmaVolTargetLowCorr({})
    s.dp = Dp()
    s.wallets = SimpleNamespace(get_starting_balance=lambda: 1000.0)
    now = datetime(2030, 2, 3, tzinfo=timezone.utc)
    # sizing.Trade and trend_ema.Trade are the same class: one fake answers both questions
    closed = []
    open_ = [SimpleNamespace(pair="A/USDT")]
    monkeypatch.setattr(sizing.Trade, "get_trades_proxy", staticmethod(lambda is_open=False: open_ if is_open else closed))
    args = ("limit", 1.0, 100.0, "GTC", now, None, "long")
    assert s.confirm_trade_entry("TWIN/USDT", *args) is False
    assert s.confirm_trade_entry("OTHER/USDT", *args) is True
    # the kill switch still comes first: a 21% realized fall refuses even an uncorrelated coin
    closed.append(SimpleNamespace(close_profit_abs=-210.0, close_date_utc=datetime(2030, 1, 1, tzinfo=timezone.utc)))
    assert s.confirm_trade_entry("OTHER/USDT", *args) is False


def test_loss_guard_until_same_meaning_as_stoploss_guard():
    h = lambda n: datetime(2030, 1, 1, tzinfo=timezone.utc) + timedelta(hours=n)  # noqa: E731
    assert sizing.loss_guard_until([]) is None
    assert sizing.loss_guard_until([h(0), h(10)]) is None  # only 2 losses
    assert sizing.loss_guard_until([h(0), h(10), h(30)]) is None  # 3 losses, but not within 24h
    assert sizing.loss_guard_until([h(0), h(10), h(24)]) == h(36)  # window edge counts, pause from the 3rd
    assert sizing.loss_guard_until([h(5), h(0), h(6), h(7)]) == h(19)  # unsorted input; a 4th loss extends


def test_loss_guard_refuses_entries_after_three_losing_exits(monkeypatch):
    s = sizing.TrendEmaVolTargetLossGuard({})
    s.dp = SimpleNamespace(runmode=SimpleNamespace(value="backtest"))
    s.wallets = SimpleNamespace(get_starting_balance=lambda: 1000.0)
    t0 = datetime(2030, 1, 1, tzinfo=timezone.utc)

    def closed_trade(hours, profit):
        return SimpleNamespace(close_date_utc=t0 + timedelta(hours=hours), close_profit=profit, close_profit_abs=profit * 100)

    closed = [closed_trade(0, -0.01), closed_trade(3, 0.02), closed_trade(5, -0.004), closed_trade(8, -0.02)]
    monkeypatch.setattr(sizing.Trade, "get_trades_proxy", staticmethod(lambda is_open=False: [] if is_open else closed))

    def allowed(at_hours):
        return s.confirm_trade_entry("BTC/USDT", "limit", 1.0, 100.0, "GTC", t0 + timedelta(hours=at_hours), None, "long")

    assert allowed(9) is False  # 3 losing exits (signal exits too) in 24h -> paused until 8 + 12 = 20h
    assert allowed(19.9) is False
    assert allowed(20) is True
    closed[2] = closed_trade(5, 0.004)  # the winner between them does not count; now only 2 losses
    assert allowed(9) is True


def test_volume_confirmed_uses_only_previous_candles():
    v = pd.Series([1.0] * 20 + [1.5, 0.5, 1.0])
    out = sizing.volume_confirmed(v)
    assert not out.iloc[:20].any()  # not enough history yet
    assert out.iloc[20] and not out.iloc[21]
    assert not out.iloc[22]  # 1.0 vs mean of previous 20 (= 1.0): not above


def test_vol_confirm_only_removes_low_volume_entries():
    cls = sizing.TrendEmaVolTargetVolConfirm
    assert cls.custom_stake_amount is sizing.TrendEmaVolTarget.custom_stake_amount
    rng = np.random.default_rng(11)
    close = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, 3000)))
    df = pd.DataFrame({"close": close, "high": close * 1.004, "low": close * 0.996, "volume": rng.lognormal(0, 0.5, 3000)})
    base = sizing.TrendEmaVolTarget({})
    b = base.populate_entry_trend(base.populate_indicators(df.copy(), {}), {})
    s = cls({})
    f = s.populate_entry_trend(s.populate_indicators(df.copy(), {}), {})
    ok = sizing.volume_confirmed(df["volume"])
    kept = f["enter_long"].fillna(0) == 1
    removed = (b["enter_long"].fillna(0) == 1) & ~kept
    assert (b["enter_long"].fillna(0)[kept] == 1).all() and ok[kept].all()
    assert (~ok[removed]).all() and kept.any() and removed.any()


def test_vote9_counts_pairs_and_uses_hysteresis():
    from trend_ema import ema

    assert len(sizing.VOTE_PAIRS) == 9 and (20, 50) in sizing.VOTE_PAIRS
    rng = np.random.default_rng(5)
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, 3000))))
    votes = sizing.ema_votes(close)
    expect = sum((ema(close, f) > ema(close, s)).astype(int) for f, s in sizing.VOTE_PAIRS)
    assert (votes == expect).all() and votes.between(0, 9).all()
    cls = sizing.TrendEmaVolTargetVote9
    assert cls.custom_stake_amount is sizing.TrendEmaVolTarget.custom_stake_amount and cls.stoploss == -0.08
    df = pd.DataFrame({"close": close, "high": close, "low": close, "volume": 1.0})
    s = cls({})
    out = s.populate_exit_trend(s.populate_entry_trend(s.populate_indicators(df, {}), {}), {})
    ent, ext = out["enter_long"].fillna(0) == 1, out["exit_long"].fillna(0) == 1
    assert ent.any() and ext.any()
    assert (out.loc[ent, "votes"] >= 5).all() and (out["votes"].shift(1)[ent] < 5).all()
    assert (out.loc[ent, "close"] > out.loc[ent, "ema_trend"]).all()
    assert (out.loc[ext, "votes"] <= 3).all() and (out["votes"].shift(1)[ext] > 3).all()
    assert not (out["votes"] == 4)[ent | ext].any()  # 4 votes: neither enter nor exit
    assert not ent.iloc[0] and not ext.iloc[0]  # no history on the first candle: never an event


def test_vote9_neighbours_only_move_thresholds():
    assert (sizing.TrendEmaVolTargetVote9.vote_enter, sizing.TrendEmaVolTargetVote9.vote_exit) == (5, 3)
    assert (sizing.VTVote4x2.vote_enter, sizing.VTVote4x2.vote_exit) == (4, 2)
    assert (sizing.VTVote6x4.vote_enter, sizing.VTVote6x4.vote_exit) == (6, 4)
    assert sizing.VTVote4x2.populate_entry_trend is sizing.TrendEmaVolTargetVote9.populate_entry_trend


def test_chandelier_only_after_one_r():
    ce = sizing.chandelier_exit
    # +7% so far: not yet +1R (8%), never exits even on a deep pullback
    assert not ce(100.0, 107.0, 90.0, 2.0, -0.08)
    # +10% seen, line = 110 - 3 x 2 = 104
    assert ce(100.0, 110.0, 103.9, 2.0, -0.08) and not ce(100.0, 110.0, 104.1, 2.0, -0.08)
    assert not ce(100.0, 110.0, 50.0, float("nan"), -0.08)  # no ATR yet: no decision
    cls = sizing.TrendEmaVolTargetChandelier
    assert cls.stoploss == -0.08 and cls.populate_exit_trend is sizing.TrendEmaVolTarget.populate_exit_trend
    assert cls.custom_stake_amount is sizing.TrendEmaVolTarget.custom_stake_amount


def test_chandelier_custom_exit_reads_last_candle():
    s = sizing.TrendEmaVolTargetChandelier({})
    df = pd.DataFrame({"close": [103.0], "atr22": [2.0]})
    s.dp = SimpleNamespace(get_analyzed_dataframe=lambda pair, tf: (df, None))
    trade = SimpleNamespace(open_rate=100.0, max_rate=110.0)
    now = datetime(2030, 1, 1, tzinfo=timezone.utc)
    assert s.custom_exit("BTC/USDT", trade, now, 103.0, 0.03) == "chandelier"
    trade.max_rate = 107.0
    assert s.custom_exit("BTC/USDT", trade, now, 103.0, 0.03) is None


def test_letrun_refuses_cross_exit_only_after_one_r():
    assert sizing.reached_one_r(100.0, 108.0, -0.08) and not sizing.reached_one_r(100.0, 107.9, -0.08)
    assert not sizing.reached_one_r(100.0, None, -0.08)
    s = sizing.TrendEmaVolTargetLetRun({})
    now = datetime(2030, 1, 1, tzinfo=timezone.utc)
    young = SimpleNamespace(open_rate=100.0, max_rate=105.0)
    winner = SimpleNamespace(open_rate=100.0, max_rate=112.0)
    args = ("limit", 1.0, 100.0, "GTC")
    assert s.confirm_trade_exit("BTC/USDT", young, *args, "ema_cross_down", now) is True
    assert s.confirm_trade_exit("BTC/USDT", winner, *args, "ema_cross_down", now) is False
    assert s.confirm_trade_exit("BTC/USDT", winner, *args, "stop_loss", now) is True  # the stop always works
    df = pd.DataFrame({"close": [104.0], "ema_letrun": [105.0]})
    s.dp = SimpleNamespace(get_analyzed_dataframe=lambda pair, tf: (df, None))
    assert s.custom_exit("BTC/USDT", winner, now, 104.0, 0.04) == "letrun_ema100"
    assert s.custom_exit("BTC/USDT", young, now, 104.0, 0.04) is None
    df.loc[0, "close"] = 106.0
    assert s.custom_exit("BTC/USDT", winner, now, 106.0, 0.06) is None


def test_letrun_neighbours_and_indicator():
    from trend_ema import ema

    assert (sizing.TrendEmaVolTargetLetRun.letrun_ema, sizing.VTLetRun75.letrun_ema, sizing.VTLetRun150.letrun_ema) == (100, 75, 150)
    rng = np.random.default_rng(2)
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 1200))))
    df = pd.DataFrame({"close": close, "high": close, "low": close, "volume": 1.0})
    out = sizing.VTLetRun150({}).populate_indicators(df, {})
    assert np.allclose(out["ema_letrun"], ema(close, 150))


def test_vote_share_and_vote_size_stake():
    assert sizing.vote_share(9) == 1.0 and sizing.vote_share(3) == pytest.approx(1 / 3)
    assert sizing.vote_share(float("nan")) == 1.0 and sizing.vote_share(0) == 0.0
    cls = sizing.TrendEmaVolTargetVoteSize
    assert cls.populate_entry_trend is sizing.TrendEmaVolTarget.populate_entry_trend
    assert cls.populate_exit_trend is sizing.TrendEmaVolTarget.populate_exit_trend and cls.stoploss == -0.08
    base, s = sizing.TrendEmaVolTarget({}), cls({})
    df = pd.DataFrame({"rvol": [0.9], "votes": [6.0]})
    for x in (base, s):
        x.wallets = SimpleNamespace(get_total_stake_amount=lambda: 1000.0)
        x.dp = SimpleNamespace(get_analyzed_dataframe=lambda pair, tf: (df, None))
    now = datetime(2030, 1, 1, tzinfo=timezone.utc)
    args = ("BTC/USDT", now, 100.0, 50.0, 5.0, 1000.0, 1.0, None, "long")
    assert s.custom_stake_amount(*args) == pytest.approx(base.custom_stake_amount(*args) * 6 / 9)


def test_obv_signs_volume_by_close_direction():
    df = pd.DataFrame({"close": [10.0, 11.0, 10.5, 10.5, 12.0], "volume": [5.0, 2.0, 3.0, 4.0, 1.0]})
    assert list(sizing.obv(df)) == [0.0, 2.0, -1.0, -1.0, 0.0]


def test_obv_strategy_only_swaps_the_trend_filter():
    from trend_ema import crossed_above, ema

    cls = sizing.TrendEmaVolTargetObv
    assert cls.populate_exit_trend is sizing.TrendEmaVolTarget.populate_exit_trend and cls.stoploss == -0.08
    assert (cls.obv_trend, sizing.VTObv150.obv_trend, sizing.VTObv250.obv_trend) == (200, 150, 250)
    rng = np.random.default_rng(8)
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, 3000))))
    df = pd.DataFrame({"close": close, "high": close, "low": close, "volume": rng.lognormal(0, 0.5, 3000)})
    s = cls({})
    out = s.populate_entry_trend(s.populate_indicators(df, {}), {})
    ent = out["enter_long"].fillna(0) == 1
    expect = crossed_above(out["ema_fast"], out["ema_slow"]) & (out["obv"] > ema(out["obv"], 200))
    assert ent.any() and (ent == expect).all()


def test_participation_uses_previous_candles_only():
    v = pd.Series([1.0] * 800)
    assert not sizing.participation_rising(v).any()  # flat: never "rising"
    v.iloc[-168:] = 3.0  # the last 7 days busier...
    out = sizing.participation_rising(v)
    assert not out.iloc[-168] and out.iloc[-1]  # ...but the first busy candle itself is not counted yet
    cls = sizing.TrendEmaVolTargetPartic
    assert cls.populate_exit_trend is sizing.TrendEmaVolTarget.populate_exit_trend
    assert (cls.partic_short, sizing.VTPartic3d.partic_short, sizing.VTPartic14d.partic_short) == (168, 72, 336)


def test_fear_block_uses_previous_day_and_allows_missing(monkeypatch):
    fng = pd.Series([10.0, 50.0], index=pd.to_datetime(["2030-01-01", "2030-01-02"], utc=True))
    monkeypatch.setattr(sizing, "load_fear_greed", lambda: fng)
    dates = pd.Series(pd.date_range("2030-01-01", periods=72, freq="h", tz="UTC"))
    n = len(dates)
    df = pd.DataFrame({"date": dates, "close": np.linspace(100, 110, n), "high": 111.0, "low": 99.0, "volume": 1.0})
    s = sizing.TrendEmaVolTargetFearBlock({})
    out = s.populate_indicators(df, {})
    assert out["fng"].iloc[:24].isna().all()  # day 1: no previous day -> unknown
    assert (out["fng"].iloc[24:48] == 10.0).all() and (out["fng"].iloc[48:] == 50.0).all()
    out["enter_long"] = 1
    out["enter_tag"] = "x"
    monkeypatch.setattr(sizing.TrendEmaVolTarget, "populate_entry_trend", lambda self, d, m: d)
    res = s.populate_entry_trend(out, {})
    assert (res["enter_long"].iloc[:24] == 1).all()  # unknown -> allowed
    assert (res["enter_long"].iloc[24:48] == 0).all()  # yesterday 10 <= 24 -> blocked
    assert (res["enter_long"].iloc[48:] == 1).all()
    assert (sizing.VTFear19.fear_max, sizing.VTFear29.fear_max) == (19, 29)


def test_strategy_modules_import_siblings_only_at_module_level():
    """Freqtrade adds user_data/strategies to sys.path only while loading a file: an import of a
    sibling module inside a method fails later unless that module was already loaded (T145 crash)."""
    import ast

    src = (Path(__file__).resolve().parent.parent / "user_data" / "strategies" / "sizing.py").read_text()
    siblings = {p.stem for p in (Path(__file__).resolve().parent.parent / "user_data" / "strategies").glob("*.py")}
    top = {n.module for n in ast.parse(src).body if isinstance(n, ast.ImportFrom)}
    lazy = {n.module for f in ast.walk(ast.parse(src)) if isinstance(f, ast.FunctionDef)
            for n in ast.walk(f) if isinstance(n, ast.ImportFrom)}  # fmt: skip
    assert (lazy & siblings) <= top, f"import these at module level: {sorted((lazy & siblings) - top)}"


def test_fear_exit_closes_only_on_known_extreme_fear():
    s = sizing.TrendEmaVolTargetFearExit({})
    now = datetime(2030, 1, 2, tzinfo=timezone.utc)
    trade = SimpleNamespace(open_rate=100.0)
    for value, expect in ((10.0, "fear_exit"), (24.0, "fear_exit"), (25.0, None), (float("nan"), None)):
        df = pd.DataFrame({"fng": [value]})
        s.dp = SimpleNamespace(get_analyzed_dataframe=lambda pair, tf, d=df: (d, None))
        assert s.custom_exit("BTC/USDT", trade, now, 100.0, 0.0) == expect
    assert sizing.TrendEmaVolTargetFearExit.populate_entry_trend is sizing.TrendEmaVolTarget.populate_entry_trend
    assert (sizing.VTFearExit19.fear_max, sizing.VTFearExit29.fear_max) == (19, 29)


def test_spike_days_use_only_the_days_before():
    idx = pd.date_range("2030-01-01", periods=35, freq="D", tz="UTC")
    views = pd.Series(100.0, index=idx)
    views.iloc[32] = 301.0  # > 3 x median(100) of the 30 days before
    views.iloc[33] = 300.0  # not above 3 x 100
    out = sizing.spike_days(views)
    assert out.iloc[:30].isna().all()  # not a full 30-day window yet
    assert out.iloc[32] == 1.0 and out.iloc[33] == 0.0 and out.iloc[31] == 0.0


def test_wiki_spike_blocks_the_next_day_only(monkeypatch, tmp_path):
    import json as _json

    days = {f"2030-01-{d:02d}": 100 for d in range(1, 32)}
    days["2030-02-01"] = 500  # spike on Feb 1 -> entries blocked on Feb 2 only
    days["2030-02-02"] = 100
    f = tmp_path / "wiki.json"
    f.write_text(_json.dumps(days))
    monkeypatch.setattr(sizing, "WIKI_FILE", f)
    dates = pd.Series(pd.date_range("2030-02-01", periods=72, freq="h", tz="UTC"))
    df = pd.DataFrame({"date": dates, "close": np.linspace(100, 101, 72), "high": 102.0, "low": 99.0, "volume": 1.0})
    s = sizing.TrendEmaVolTargetWikiSpike({})
    out = s.populate_indicators(df, {})
    out["enter_long"], out["enter_tag"] = 1, "x"
    monkeypatch.setattr(sizing.TrendEmaVolTarget, "populate_entry_trend", lambda self, d, m: d)
    res = s.populate_entry_trend(out, {})
    assert (res["enter_long"].iloc[:24] == 1).all()  # Feb 1: uses Jan 31 (no spike)
    assert (res["enter_long"].iloc[24:48] == 0).all()  # Feb 2: uses Feb 1 (spike)
    assert (res["enter_long"].iloc[48:] == 1).all()
    assert (sizing.VTWikiSpike2x.spike_mult, sizing.VTWikiSpike4x.spike_mult) == (2.0, 4.0)


def test_wiki_missing_file_means_no_filter(monkeypatch, tmp_path):
    monkeypatch.setattr(sizing, "WIKI_FILE", tmp_path / "missing.json")
    assert sizing.load_daily_json(tmp_path / "missing.json").empty
