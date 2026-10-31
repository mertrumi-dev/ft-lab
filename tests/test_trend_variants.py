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
