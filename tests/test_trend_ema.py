"""Tests for the TrendEma strategy: signals, risk math and locked-in risk rules.

Needs freqtrade installed (pip install -r requirements-dev.txt).
"""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("freqtrade")

ROOT = Path(__file__).resolve().parent.parent
STRATEGY_FILE = ROOT / "user_data" / "strategies" / "trend_ema.py"
CONFIG_FILE = ROOT / "user_data" / "config" / "config.json"

spec = importlib.util.spec_from_file_location("trend_ema", STRATEGY_FILE)
trend_ema = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trend_ema)


def make_candles(closes) -> pd.DataFrame:
    closes = np.asarray(closes, dtype=float)
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=len(closes), freq="1h", tz="UTC"),
            "open": closes,
            "high": closes * 1.001,
            "low": closes * 0.999,
            "close": closes,
            "volume": np.full(len(closes), 100.0),
        }
    )


def run_strategy(closes) -> pd.DataFrame:
    strategy = trend_ema.TrendEma({})
    df = make_candles(closes)
    df = strategy.populate_indicators(df, {"pair": "BTC/USDT"})
    df = strategy.populate_entry_trend(df, {"pair": "BTC/USDT"})
    df = strategy.populate_exit_trend(df, {"pair": "BTC/USDT"})
    return df


# --- helpers ---------------------------------------------------------------


def test_crossed_above_fires_only_on_the_crossing_candle():
    a = pd.Series([1, 2, 3, 4])
    b = pd.Series([2, 2, 2, 2])
    assert crossed(trend_ema.crossed_above, a, b) == [2]


def test_crossed_below_fires_only_on_the_crossing_candle():
    a = pd.Series([3, 2, 1, 0])
    b = pd.Series([2, 2, 2, 2])
    assert crossed(trend_ema.crossed_below, a, b) == [2]


def crossed(func, a, b):
    return list(np.flatnonzero(func(a, b).to_numpy()))


def test_risk_based_stake_example_from_docs():
    # 1000 capital, 1% risk, -8% stop -> 125
    assert trend_ema.risk_based_stake(1000, 0.01, -0.08, 0.25) == pytest.approx(125)


def test_risk_based_stake_is_capped():
    # very tight stop would ask for 500, cap is 25% -> 250
    assert trend_ema.risk_based_stake(1000, 0.01, -0.02, 0.25) == pytest.approx(250)


def test_drawdown_from_peak():
    # 1000 -> 1200 (peak) -> 900: fell 300 from 1200 = 25%
    assert trend_ema.drawdown_from_peak(1000, [200, -300]) == pytest.approx(0.25)
    assert trend_ema.drawdown_from_peak(1000, []) == 0.0


# --- signals ---------------------------------------------------------------


def test_entry_in_uptrend_after_dip():
    # long climb (above EMA200), short dip, then recovery -> fast EMA crosses up
    closes = np.concatenate(
        [np.linspace(100, 200, 400), np.linspace(200, 185, 40), np.linspace(185, 230, 60)]
    )
    df = run_strategy(closes)
    entries = df.index[df["enter_long"] == 1]
    assert len(entries) >= 1
    assert (df.loc[entries, "close"] > df.loc[entries, "ema_trend"]).all()
    assert (df.loc[entries, "enter_tag"] == "ema_cross_up").all()


def test_no_entry_in_downtrend():
    # steady fall with strong bounces: fast EMA does cross above slow EMA,
    # but price stays under EMA200, so the trend filter must block every entry
    t = np.arange(800)
    closes = np.linspace(300, 100, 800) + 15 * np.sin(t / 15)
    df = run_strategy(closes)
    after_warmup = df.iloc[trend_ema.TrendEma.startup_candle_count :]
    crosses = trend_ema.crossed_above(after_warmup["ema_fast"], after_warmup["ema_slow"])
    assert crosses.sum() > 0  # the situation really happens
    assert after_warmup.get("enter_long", pd.Series(dtype=float)).fillna(0).sum() == 0


def test_exit_when_trend_turns_down():
    closes = np.concatenate([np.linspace(100, 200, 400), np.linspace(200, 150, 80)])
    df = run_strategy(closes)
    exits = df.index[df["exit_long"] == 1]
    assert len(exits) >= 1
    assert (df.loc[exits, "exit_tag"] == "ema_cross_down").all()


# --- locked-in risk rules ---------------------------------------------------


def test_stoploss_is_set_and_not_wider_than_8_percent():
    assert -0.08 <= trend_ema.TrendEma.stoploss < 0


def test_risk_per_trade_at_most_1_percent():
    assert 0 < trend_ema.RISK_PER_TRADE <= 0.01
    assert 0 < trend_ema.MAX_STAKE_RATIO <= 0.25


def test_kill_switch_at_most_20_percent():
    assert 0 < trend_ema.KILL_SWITCH_DRAWDOWN <= 0.20


def test_spot_only_no_shorting():
    assert trend_ema.TrendEma.can_short is False


def test_all_protections_present():
    methods = [p["method"] for p in trend_ema.TrendEma({}).protections]
    for required in ["CooldownPeriod", "StoplossGuard", "MaxDrawdown", "LowProfitPairs"]:
        assert required in methods
    assert methods.count("MaxDrawdown") == 2  # daily + weekly limit


def test_max_open_trades_at_most_3():
    assert 0 < json.loads(CONFIG_FILE.read_text())["max_open_trades"] <= 3
