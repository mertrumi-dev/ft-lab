"""Tests for round 11: TrendEmaBtcRising (BTC daily SMA50 slope gate)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("freqtrade")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "user_data" / "strategies"))
import regime  # noqa: E402
import trend_ema  # noqa: E402


def daily(close, start="2024-01-01"):
    return pd.DataFrame({"date": pd.date_range(start, periods=len(close), freq="1D", tz="UTC"),
                         "close": np.asarray(close, dtype=float)})


def hourly(start, periods):
    return pd.DataFrame({"date": pd.date_range(start, periods=periods, freq="1h", tz="UTC")})


def test_keep_risk_rules():
    cls = regime.TrendEmaBtcRising
    assert cls.stoploss == trend_ema.STOPLOSS and cls.can_short is False
    assert cls.confirm_trade_entry is trend_ema.TrendEma.confirm_trade_entry
    assert cls.custom_stake_amount is trend_ema.TrendEma.custom_stake_amount
    assert cls.populate_exit_trend is trend_ema.TrendEma.populate_exit_trend


def test_rising_and_falling():
    up = regime.btc_daily_rising(daily(np.linspace(100, 200, 100)))
    down = regime.btc_daily_rising(daily(np.linspace(200, 100, 100)))
    assert up["btc_rising"].iloc[-1] and not down["btc_rising"].iloc[-1]
    assert not up["btc_rising"].iloc[:59].any()  # SMA50 + 10-day slope needs 60 days


def test_daily_value_used_only_after_the_day_closed():
    # rising for 100 days, then a crash that turns the slope down on day index 129
    close = np.concatenate([np.linspace(100, 200, 100), np.linspace(200, 50, 60)])
    d = daily(close)
    flags = regime.btc_daily_rising(d)
    flip = flags.index[(~flags["btc_rising"]) & (flags.index > 100)][0]
    flip_day = d["date"].iloc[flip]
    h = hourly(flip_day - pd.Timedelta(hours=2), 30)
    seen = regime.attach_btc_rising(h, d)
    # during the flip day itself the strategy still sees the PREVIOUS day's value (rising)
    assert seen[h["date"] < flip_day + pd.Timedelta(days=1)].all()
    # from the next midnight on it sees "falling"
    assert not seen[h["date"] >= flip_day + pd.Timedelta(days=1)].any()


def test_future_daily_candles_do_not_change_the_past():
    close = np.concatenate([np.linspace(100, 200, 100), np.linspace(200, 50, 60)])
    h = hourly("2024-04-01", 24 * 20)
    a = regime.attach_btc_rising(h, daily(close))
    b = regime.attach_btc_rising(h, daily(np.concatenate([close[:110], np.full(50, 1000.0)])))
    cut = h["date"] < pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(days=110)
    assert a[cut].equals(b[cut])


def test_mixed_time_units_like_freqtrade():
    # Freqtrade gave us ms for one frame and us for the other: must not crash
    d = daily(np.linspace(100, 200, 100))
    d["date"] = d["date"].astype("datetime64[us, UTC]")
    h = hourly("2024-03-15", 48)
    h["date"] = h["date"].astype("datetime64[ms, UTC]")
    assert regime.attach_btc_rising(h, d).all()


@pytest.mark.parametrize("cls", regime.BTC_RISING_NEIGHBOURS, ids=lambda c: c.__name__)
def test_neighbours_change_exactly_one_number(cls):
    base = (regime.TrendEmaBtcRising.btc_sma, regime.TrendEmaBtcRising.btc_days)
    mine = (cls.btc_sma, cls.btc_days)
    assert sum(b != m for b, m in zip(base, mine)) == 1
    assert cls.confirm_trade_entry is trend_ema.TrendEma.confirm_trade_entry


def test_neighbour_parameters_reach_the_gate():
    # a 100-day rise then flat: slope over 5 days turns False sooner than over 15
    close = np.concatenate([np.linspace(100, 200, 100), np.full(40, 200.0)])
    d = daily(close)
    r5 = regime.btc_daily_rising(d, 50, 5)["btc_rising"]
    r15 = regime.btc_daily_rising(d, 50, 15)["btc_rising"]
    assert r5.sum() != r15.sum()


def test_btc_rising_pyramid_combines_exactly_two_parents():
    import trend_variants as tv

    cls = regime.TrendEmaBtcRisingPyramid
    assert cls.populate_entry_trend is regime.TrendEmaBtcRising.populate_entry_trend
    assert cls.populate_indicators is regime.TrendEmaBtcRising.populate_indicators
    assert cls.adjust_trade_position is tv.TrendEmaPyramid.adjust_trade_position
    assert cls.custom_stoploss is tv.TrendEmaPyramid.custom_stoploss
    assert cls.position_adjustment_enable is True and cls.max_entry_position_adjustment == 1
    assert cls.confirm_trade_entry is trend_ema.TrendEma.confirm_trade_entry
    assert cls.stoploss == trend_ema.STOPLOSS


def test_gap_only_removes_entries():
    close = np.concatenate([np.linspace(100, 200, 600), np.linspace(200, 185, 60), np.linspace(185, 260, 340)])
    df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=len(close), freq="1h", tz="UTC"),
                       "open": close, "high": close, "low": close, "close": close, "volume": 100.0})
    base, gap = regime.TrendEmaBtcRising({}), regime.TrendEmaBtcRisingGap({})
    a = base.populate_entry_trend(base.populate_indicators(df.copy(), {"pair": "X"}), {})
    b = gap.populate_entry_trend(gap.populate_indicators(df.copy(), {"pair": "X"}), {})
    assert (b["enter_long"].fillna(0) <= a["enter_long"].fillna(0)).all()
    hits = b.index[b["enter_long"] == 1]
    assert all(b["close"][i] >= b["ema_trend"][i] * 1.01 for i in hits)
    assert regime.TrendEmaBtcRisingGap.populate_exit_trend is trend_ema.TrendEma.populate_exit_trend


class _T:
    def __init__(self, open_rate, max_rate):
        self.open_rate, self.max_rate = open_rate, max_rate


def test_breakeven_stop_only_after_trigger():
    s = regime.TrendEmaGapBreakeven({})
    # never reached +5%: keep the normal stop
    assert s.custom_stoploss("X", _T(100, 104), None, 103, 0.03, False) is None
    # reached +6%, now at 103: stop at 100.5 -> (103-100.5)/103 below current
    sl = s.custom_stoploss("X", _T(100, 106), None, 103, 0.03, False)
    assert sl == pytest.approx((103 - 100.5) / 103, rel=1e-3)
    assert regime.TrendEmaGapBreakeven.confirm_trade_entry is trend_ema.TrendEma.confirm_trade_entry
    assert regime.TrendEmaGapBreakeven.stoploss == trend_ema.STOPLOSS


def test_gap_risk2_is_research_only_and_live_risk_stays_1pct():
    cls = regime.TrendEmaBtcRisingGapRisk2
    assert trend_ema.RISK_PER_TRADE == 0.01  # the live rule is untouched
    assert regime.GAP_RESEARCH_RISK == 2 * trend_ema.RISK_PER_TRADE
    assert trend_ema.MAX_STAKE_RATIO == 0.25
    assert cls.custom_stake_amount is not trend_ema.TrendEma.custom_stake_amount
    # outside backtest (no dp / dry-run) every entry is refused
    assert cls({}).confirm_trade_entry("BTC/USDT", "limit", 1, 1, "GTC", None, None, "long") is False

    class _Rm:
        value = "dry_run"

    class _Dp:
        runmode = _Rm()

    s = cls({})
    s.dp = _Dp()
    assert s.confirm_trade_entry("BTC/USDT", "limit", 1, 1, "GTC", None, None, "long") is False
    compose = (Path(__file__).resolve().parent.parent / "docker-compose.yml").read_text()
    assert "Risk2" not in compose


def test_gap4h_only_changes_timeframe():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import ft

    cls = regime.TrendEmaBtcRisingGap4h
    assert cls.timeframe == "4h" and regime.TrendEmaBtcRisingGap.timeframe == "1h"
    assert cls.populate_entry_trend is regime.TrendEmaBtcRisingGap.populate_entry_trend
    assert ft.timeframe_of("TrendEmaBtcRisingGap4h") == "4h"
