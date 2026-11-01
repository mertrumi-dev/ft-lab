"""Tests for the market-mood filters (TrendEmaFng, TrendEmaCalm) and scripts/sentiment.py."""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("freqtrade")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "user_data" / "strategies"))
sys.path.insert(0, str(ROOT / "scripts"))
import sentiment  # noqa: E402
import trend_ema  # noqa: E402
import trend_sentiment as ts  # noqa: E402

CLASSES = [ts.TrendEmaFng, ts.TrendEmaCalm]


def candles(close, start="2024-01-01"):
    close = np.asarray(close, dtype=float)
    return pd.DataFrame(
        {
            "date": pd.date_range(start, periods=len(close), freq="1h", tz="UTC"),
            "open": close,
            "high": close * 1.001,
            "low": close * 0.999,
            "close": close,
            "volume": np.full(len(close), 100.0),
        }
    )


@pytest.mark.parametrize("cls", CLASSES, ids=lambda c: c.__name__)
def test_keep_risk_rules(cls):
    assert cls.stoploss == trend_ema.STOPLOSS
    assert cls.can_short is False
    assert "StoplossGuard" in [p["method"] for p in cls({}).protections]
    # kill switch + stale-data guard live here; these classes must not override it
    assert cls.confirm_trade_entry is trend_ema.TrendEma.confirm_trade_entry
    assert cls.custom_stake_amount is trend_ema.TrendEma.custom_stake_amount


# --- Fear & Greed ---------------------------------------------------------------


def test_sentiment_parse_converts_timestamps_to_utc_days_oldest_first():
    payload = {"data": [{"value": "34", "timestamp": "1793491200"}, {"value": "30", "timestamp": "1517443200"}]}
    days = sentiment.parse(payload)
    assert list(days) == ["2018-02-01", "2026-11-01"]
    assert days["2026-11-01"] == 34


def test_fng_uses_only_previous_day_no_lookahead():
    fng = pd.Series([10.0, 90.0], index=pd.to_datetime(["2024-01-01", "2024-01-02"], utc=True))
    dates = pd.Series(pd.date_range("2024-01-02", periods=48, freq="1h", tz="UTC"))
    seen = ts.fng_for_candles(dates, fng)
    # every candle of Jan 2 sees Jan 1's value (10), never Jan 2's own (90)
    assert (seen.iloc[:24] == 10.0).all()
    # Jan 3 candles see Jan 2's value
    assert (seen.iloc[24:] == 90.0).all()


def test_fng_missing_day_is_nan_not_a_guess():
    fng = pd.Series([50.0], index=pd.to_datetime(["2024-01-01"], utc=True))
    dates = pd.Series(pd.date_range("2024-01-05", periods=3, freq="1h", tz="UTC"))
    assert ts.fng_for_candles(dates, fng).isna().all()


def test_load_fear_greed_missing_file_is_empty(tmp_path):
    assert ts.load_fear_greed(tmp_path / "nope.json").empty


def test_load_fear_greed_reads_file(tmp_path):
    p = tmp_path / "fg.json"
    p.write_text(json.dumps({"2024-01-01": 80, "2024-01-02": 20}))
    s = ts.load_fear_greed(p)
    assert s.loc[pd.Timestamp("2024-01-02", tz="UTC")] == 20


def _rising_after_fall():
    # uptrend, a short dip (EMA20 drops under EMA50), then the uptrend resumes:
    # TrendEma buys when EMA20 crosses back up while price is above EMA200
    return np.concatenate([np.linspace(100, 200, 600), np.linspace(200, 185, 60), np.linspace(185, 260, 340)])


def test_fng_blocks_entries_after_extreme_greed(monkeypatch):
    close = _rising_after_fall()
    df = candles(close)
    days = pd.date_range("2023-12-01", "2024-03-01", freq="1D", tz="UTC")
    monkeypatch.setattr(ts, "load_fear_greed", lambda: pd.Series(90.0, index=days))
    strat = ts.TrendEmaFng({})
    out = strat.populate_entry_trend(strat.populate_indicators(df, {"pair": "BTC/USDT"}), {})
    assert (out["enter_long"].fillna(0) == 0).all()


def test_fng_without_data_behaves_like_trend_ema(monkeypatch):
    close = _rising_after_fall()
    monkeypatch.setattr(ts, "load_fear_greed", lambda: pd.Series(dtype=float))
    strat, base = ts.TrendEmaFng({}), trend_ema.TrendEma({})
    out = strat.populate_entry_trend(strat.populate_indicators(candles(close), {"pair": "BTC/USDT"}), {})
    ref = base.populate_entry_trend(base.populate_indicators(candles(close), {"pair": "BTC/USDT"}), {})
    assert ref["enter_long"].fillna(0).sum() > 0
    assert (out["enter_long"].fillna(0) == ref["enter_long"].fillna(0)).all()


# --- Volatility regime ------------------------------------------------------------


def test_wild_flag_uses_only_past_candles():
    close = np.full(1000, 100.0)
    df = candles(close)
    df.loc[900:, "high"] = 110.0  # volatility jumps at candle 900
    df.loc[900:, "low"] = 90.0
    wild = ts.atr_pct_is_wild(df, window=100)
    assert not wild.iloc[:900].any()
    assert wild.iloc[900]  # the jump candle is wild compared with the calm past
    # changing the FUTURE must not change today's flag
    df2 = df.copy()
    df2.loc[950:, ["high", "low"]] = 100.0
    assert ts.atr_pct_is_wild(df2, window=100).iloc[:950].equals(wild.iloc[:950])


def test_calm_never_adds_entries():
    close = _rising_after_fall() * (1 + 0.02 * np.sin(np.arange(1000) / 3))
    strat, base = ts.TrendEmaCalm({}), trend_ema.TrendEma({})
    out = strat.populate_entry_trend(strat.populate_indicators(candles(close), {"pair": "BTC/USDT"}), {})
    ref = base.populate_entry_trend(base.populate_indicators(candles(close), {"pair": "BTC/USDT"}), {})
    assert (out["enter_long"].fillna(0) <= ref["enter_long"].fillna(0)).all()


def test_calm_startup_covers_window():
    assert ts.TrendEmaCalm.startup_candle_count >= ts.CALM_WINDOW + 2 * trend_ema.TREND_EMA
