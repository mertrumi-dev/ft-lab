"""Tests for scripts/regimes.py (regime labels and per-regime stats) on synthetic data."""

import sys
from pathlib import Path

import numpy as np
import pytest

pd = pytest.importorskip("pandas")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import ft  # noqa: E402
import regimes  # noqa: E402


def btc_days():
    up, down = np.linspace(100, 300, 400), np.linspace(300, 100, 400)
    idx = pd.date_range("2020-01-01", periods=800, freq="1D", tz="UTC")
    return pd.Series(np.concatenate([up, down]), index=idx)


def test_label_days_bull_then_bear():
    d = regimes.label_days(btc_days())
    assert d["trend"].iloc[:50].eq("bull").all()  # first labelled days: steady rise
    assert d["trend"].iloc[-50:].eq("bear").all()
    assert set(d["trend"]) <= {"bull", "bear", "sideways"}


def test_hourly_labels_use_previous_closed_day():
    days = regimes.label_days(btc_days())
    first = days.index[0]
    idx = pd.date_range(first, periods=48, freq="1h")
    lab = regimes.hourly_labels(days, idx)
    assert lab["trend"].iloc[:24].isna().all()  # day 1 is known only from day 2 00:00
    assert lab["trend"].iloc[24] == days["trend"].iloc[0]


def test_regime_stats_and_trades():
    idx = pd.date_range("2021-01-01", periods=4, freq="1h", tz="UTC")
    eq = pd.Series([1.0, 1.1, 1.1, 0.99], index=idx)
    lab = pd.Series(["bull", "bull", "bear", "bear"], index=idx)
    s = regimes.regime_stats(eq, lab, pd.Series([0.0, 1.1, 0.0, 0.99], index=idx))
    assert s["bull"]["return"] == pytest.approx(0.1) and s["bear"]["return"] == pytest.approx(-0.1)
    assert s["bear"]["max_drawdown"] == pytest.approx(0.1) and s["bull"]["in_market"] == pytest.approx(0.5)
    t = regimes.trade_stats([{"open_date": "2021-01-01 00:30:00", "profit_abs": 5},
                             {"open_date": "2021-01-01 03:10:00", "profit_abs": -1}], lab)
    assert t["bull"] == {"trades": 1, "wins": 1, "win_rate": 1.0} and t["bear"]["win_rate"] == 0.0
    text = regimes.render("x", "trend", ["A"], {"A": s}, {"A": t})
    assert "| A |" in text and "boğa" in text and "1 işlem %100 kazanç" in text


def test_ft_regimes_refuses_validation():
    with pytest.raises(SystemExit):
        ft.parse_args(["regimes", "--slice", "validation"])
    c = ft.build_commands(ft.parse_args(["regimes", "--slice", "train", "--no-kill-switch"]))[-1]
    assert "/freqtrade/scripts/regimes.py" in c and "no_kill_switch" in " ".join(c)
