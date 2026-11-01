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

VARIANTS = [
    tv.TrendEmaAtr, tv.TrendEmaAtrTrail, tv.TrendEma4h, tv.TrendBreakout,
    tv.TrendEmaAtrWide, tv.TrendEmaSlow, tv.TrendEmaMulti, tv.TrendEmaBtc,
    *tv.SLOW_NEIGHBOURS, tv.TrendEmaAdx, tv.TrendEmaLongTrend, tv.TrendEmaHold,
    tv.TrendEmaExitConfirm, tv.TrendEmaSlope, tv.TrendEmaEntryConfirm, tv.EntryConfirm2, tv.EntryConfirm4, tv.TrendEmaPyramid, tv.Pyramid3, tv.Pyramid6, tv.TrendEmaPyramidBtc,
]  # fmt: skip


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


# --- Round 2 -----------------------------------------------------------------


def test_atr_wide_only_changes_multiplier():
    assert tv.TrendEmaAtrWide.atr_mult == 5.0
    assert tv.TrendEmaAtr.atr_mult == tv.ATR_STOP_MULT


def test_slow_variant_uses_slower_averages():
    close = np.linspace(100, 200, 1500)
    df = tv.TrendEmaSlow({}).populate_indicators(candles(close), {"pair": "BTC/USDT"})
    # in a steady rise a slower average lags further behind the price
    last = df.iloc[-1]
    assert last["close"] > last["ema_fast"] > last["ema_slow"] > last["ema_trend"]
    assert tv.TrendEmaSlow.startup_candle_count >= 600 * 2


@pytest.mark.parametrize("cls", tv.SLOW_NEIGHBOURS, ids=lambda c: c.__name__)
def test_slow_neighbours_change_exactly_one_number(cls):
    base = (tv.TrendEmaSlow.fast_len, tv.TrendEmaSlow.slow_len, tv.TrendEmaSlow.trend_len)
    mine = (cls.fast_len, cls.slow_len, cls.trend_len)
    changed = [b != m for b, m in zip(base, mine)]
    assert sum(changed) == 1
    assert cls.fast_len < cls.slow_len < cls.trend_len
    assert cls.startup_candle_count >= 2 * cls.trend_len


def test_multi_enters_once_when_votes_turn_bullish():
    # long fall, then long rise: votes go 0 -> 3, entry only on the switch candle
    close = np.concatenate([np.linspace(200, 100, 800), np.linspace(100, 300, 800)])
    strat = tv.TrendEmaMulti({})
    df = strat.populate_indicators(candles(close), {"pair": "BTC/USDT"})
    df = strat.populate_entry_trend(df, {"pair": "BTC/USDT"})
    df = strat.populate_exit_trend(df, {"pair": "BTC/USDT"})
    assert df["votes"].iloc[700] == 0 and df["votes"].iloc[-1] == 3
    entries = df.index[df["enter_long"] == 1]
    assert len(entries) == 1
    # on the entry candle at least 2 of 3 pairs say "up", the candle before fewer
    i = entries[0]
    assert df["votes"].iloc[i] >= 2 and df["votes"].iloc[i - 1] < 2
    assert df["close"].iloc[i] > df["ema_trend"].iloc[i]


def test_btc_filter_without_data_provider_allows_entries():
    # no dp (unit test / plotting): filter must not silently block everything
    close = np.concatenate([np.linspace(200, 100, 500), np.linspace(100, 300, 500)])
    strat = tv.TrendEmaBtc({})
    base = trend_ema.TrendEma({})
    df = strat.populate_entry_trend(strat.populate_indicators(candles(close), {"pair": "ETH/USDT"}), {})
    ref = base.populate_entry_trend(base.populate_indicators(candles(close), {"pair": "ETH/USDT"}), {})
    assert df["btc_bull"].all()
    assert (df["enter_long"].fillna(0) == ref["enter_long"].fillna(0)).all()


class _FakeDp:
    def __init__(self, btc):
        self.btc = btc

    def get_pair_dataframe(self, pair, timeframe):
        return self.btc


def test_btc_filter_blocks_entries_when_btc_is_down():
    rising = np.concatenate([np.linspace(200, 100, 500), np.linspace(100, 300, 500)])
    falling_btc = np.linspace(300, 100, 1000)  # BTC below its EMA200 the whole time
    strat = tv.TrendEmaBtc({})
    strat.dp = _FakeDp(candles(falling_btc))
    df = strat.populate_indicators(candles(rising), {"pair": "ETH/USDT"})
    df = strat.populate_entry_trend(df, {"pair": "ETH/USDT"})
    assert not df["btc_bull"].iloc[-300:].any()
    assert (df["enter_long"].fillna(0) == 0).all()


# --- Round 3 -----------------------------------------------------------------


def test_adx_high_in_steady_trend_low_in_chop():
    n = 400
    trend = np.linspace(100, 200, n)
    df_trend = candles(trend, high=trend + 0.5, low=trend - 0.5)
    chop = 100 + 2 * np.sin(np.arange(n))  # back and forth every candle
    df_chop = candles(chop, high=chop + 1, low=chop - 1)
    assert tv.adx(df_trend).iloc[-1] > 50
    assert tv.adx(df_chop).iloc[-1] < 20


def _entries(cls, df):
    s = cls({})
    df = s.populate_indicators(df.copy(), {"pair": "BTC/USDT"})
    return s.populate_entry_trend(df, {"pair": "BTC/USDT"})


@pytest.mark.parametrize("cls", [tv.TrendEmaAdx, tv.TrendEmaLongTrend], ids=lambda c: c.__name__)
def test_round3_filters_only_remove_entries(cls):
    # a filter may block TrendEma's entries but never add new ones
    t = np.arange(3000)
    close = 100 + t * 0.02 + 15 * np.sin(t / 15)
    df = candles(close, high=close + 1, low=close - 1)
    base = _entries(trend_ema.TrendEma, df)["enter_long"].fillna(0)
    mine = _entries(cls, df)["enter_long"].fillna(0)
    assert base.sum() > 0
    assert ((mine == 1) <= (base == 1)).all()


def test_long_trend_blocks_entries_below_long_average():
    # long fall then short bounce: EMA200 may turn but price stays under EMA1000
    close = np.concatenate([np.linspace(300, 100, 2500), np.linspace(100, 140, 400)])
    df = candles(close, high=close + 0.5, low=close - 0.5)
    out = _entries(tv.TrendEmaLongTrend, df)
    blocked = out["close"] <= out["ema_long"]
    assert (out.loc[blocked, "enter_long"].fillna(0) == 0).all()


def test_hold_exits_only_when_close_crosses_below_trend_line():
    t = np.arange(3000)
    close = 100 + t * 0.02 + 15 * np.sin(t / 15)
    df = candles(close, high=close + 1, low=close - 1)
    s = tv.TrendEmaHold({})
    df = s.populate_exit_trend(s.populate_indicators(df, {"pair": "BTC/USDT"}), {"pair": "BTC/USDT"})
    exits = df.index[df["exit_long"].fillna(0) == 1]
    assert len(exits) > 0
    for i in exits:
        assert df["close"].iloc[i] < df["ema_trend"].iloc[i]
        assert df["close"].iloc[i - 1] >= df["ema_trend"].iloc[i - 1]
    # entry rule untouched
    base = trend_ema.TrendEma({})
    ref = base.populate_entry_trend(base.populate_indicators(candles(close, close + 1, close - 1), {}), {})
    mine = s.populate_entry_trend(df, {})
    assert (ref["enter_long"].fillna(0) == mine["enter_long"].fillna(0)).all()


def _cross_frame(fast, slow):
    df = candles([100.0] * len(fast))
    df["ema_fast"], df["ema_slow"], df["ema_trend"] = fast, slow, 50.0
    return df


def test_exit_confirm_ignores_a_two_hour_dip():
    fast = [11, 9, 9, 11, 11, 11]  # below for only 2 candles
    df = tv.TrendEmaExitConfirm({}).populate_exit_trend(_cross_frame(fast, [10] * 6), {})
    assert df.get("exit_long", pd.Series(0, index=df.index)).fillna(0).sum() == 0


def test_exit_confirm_sells_on_the_third_candle_below():
    fast = [11, 9, 9, 9, 9, 9]
    df = tv.TrendEmaExitConfirm({}).populate_exit_trend(_cross_frame(fast, [10] * 6), {})
    assert list(df["exit_long"].fillna(0)) == [0, 0, 0, 1, 0, 0]


def test_slope_blocks_cross_up_while_ema50_falls():
    n = 30
    fast = [9.0] * (n - 1) + [11.0]
    falling = list(np.linspace(12, 10, n))
    rising = list(np.linspace(8, 10, n))
    s = tv.TrendEmaSlope({})
    down = s.populate_entry_trend(_cross_frame(fast, falling), {})
    up = s.populate_entry_trend(_cross_frame(fast, rising), {})
    assert down["enter_long"].fillna(0).iloc[-1] == 0
    assert up["enter_long"].fillna(0).iloc[-1] == 1


def test_entry_confirm_buys_on_the_third_candle_above_only():
    fast = [9, 11, 11, 11, 11, 11]
    df = tv.TrendEmaEntryConfirm({}).populate_entry_trend(_cross_frame(fast, [10] * 6), {})
    assert list(df["enter_long"].fillna(0)) == [0, 0, 0, 1, 0, 0]


def test_entry_confirm_skips_a_short_cross_up():
    fast = [9, 11, 11, 9, 9, 9]
    df = tv.TrendEmaEntryConfirm({}).populate_entry_trend(_cross_frame(fast, [10] * 6), {})
    assert df.get("enter_long", pd.Series(0, index=df.index)).fillna(0).sum() == 0


def test_entry_confirm_needs_trend_filter():
    df = _cross_frame([9, 11, 11, 11], [10] * 4)
    df["ema_trend"] = 200.0  # close 100 below the trend line
    df = tv.TrendEmaEntryConfirm({}).populate_entry_trend(df, {})
    assert df.get("enter_long", pd.Series(0, index=df.index)).fillna(0).sum() == 0


def test_entry_confirm_neighbours():
    assert (tv.EntryConfirm2.confirm_candles, tv.EntryConfirm4.confirm_candles) == (2, 4)


class _Wallets:
    def __init__(self, capital):
        self.capital = capital

    def get_total_stake_amount(self):
        return self.capital


class _Trade:
    def __init__(self, entries, stake, open_rate=100.0, amount=1.25):
        self.nr_of_successful_entries, self.stake_amount = entries, stake
        self.open_rate, self.amount = open_rate, amount


def _pyramid(capital=1000.0):
    s = tv.TrendEmaPyramid({})
    s.wallets = _Wallets(capital)
    return s


def _adjust(s, trade, profit):
    return s.adjust_trade_position(trade, None, 104.0, profit, 5.0, 10_000.0, 104.0, 104.0, profit, profit)


def test_pyramid_adds_same_size_once_at_plus_4_percent():
    s = _pyramid()
    assert _adjust(s, _Trade(1, 125.0), 0.039) is None
    assert _adjust(s, _Trade(1, 125.0), 0.04) == pytest.approx(125.0)
    assert _adjust(s, _Trade(2, 250.0), 0.10) is None  # only one add


def test_pyramid_respects_25_percent_cap():
    assert _adjust(_pyramid(), _Trade(1, 200.0), 0.05) == pytest.approx(50.0)  # 250 - 200
    assert _adjust(_pyramid(), _Trade(1, 250.0), 0.05) is None


def test_pyramid_stop_keeps_total_risk_at_one_percent():
    # 2.4 coins at avg 102 (~245 USDT), capital 1000: 1% = 10 USDT -> stop 10/2.4 below avg
    stop = tv.pyramid_stop_price(102.0, 2.4, 1000.0, 0.01, 0.08)
    assert stop == pytest.approx(102.0 - 10 / 2.4)
    assert (102.0 - stop) * 2.4 == pytest.approx(10.0)


def test_pyramid_stop_never_wider_than_8_percent():
    # tiny position: the 1% budget would allow a huge fall, the 8% cap wins
    assert tv.pyramid_stop_price(100.0, 0.1, 1000.0, 0.01, 0.08) == pytest.approx(92.0)


def test_pyramid_single_entry_keeps_normal_stop():
    s = _pyramid()
    assert s.custom_stoploss("X", _Trade(1, 125.0), None, 100.0, 0.0, False) is None


def test_pyramid_neighbours_triggers():
    assert (tv.Pyramid3.pyramid_trigger, tv.TrendEmaPyramid.pyramid_trigger, tv.Pyramid6.pyramid_trigger) == (0.03, 0.04, 0.06)
    s = tv.Pyramid6({})
    s.wallets = _Wallets(1000.0)
    assert _adjust(s, _Trade(1, 125.0), 0.05) is None


class _Dp:
    def __init__(self, bull):
        self.df = pd.DataFrame({"btc_bull": [not bull, bull]})

    def get_analyzed_dataframe(self, pair, timeframe):
        return self.df, None


class _PTrade(_Trade):
    pair = "ETH/USDT"


def test_pyramid_btc_adds_only_in_bull_market():
    for bull, expected in ((True, 125.0), (False, None)):
        s = tv.TrendEmaPyramidBtc({})
        s.wallets, s.dp = _Wallets(1000.0), _Dp(bull)
        assert _adjust(s, _PTrade(1, 125.0), 0.05) == expected


def test_pyramid_btc_keeps_entries_of_trend_ema():
    # no BTC filter on entries: same entry function as TrendEma
    assert tv.TrendEmaPyramidBtc.populate_entry_trend is trend_ema.TrendEma.populate_entry_trend
