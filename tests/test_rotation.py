import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import rotation  # noqa: E402


def _hourly(days, slopes, start="2021-01-04"):
    idx = pd.date_range(start, periods=days * 24, freq="1h", tz="UTC")
    t = np.arange(len(idx)) / 24
    return pd.DataFrame({k: 100 * (1 + s) ** t for k, s in slopes.items()}, index=idx)


def test_picks_only_rising_coins_and_caps_at_four():
    h = _hourly(200, {"A": 0.01, "B": 0.005, "C": 0.002, "D": 0.001, "E": 0.0005, "F": -0.01})
    daily = rotation.daily_closes(dict(h.items()))
    w = rotation.target_weights(daily, daily["A"], sma_days=20)
    last = w.iloc[-1]
    assert list(last[last > 0].index) == ["A", "B", "C", "D"]
    assert last.sum() == pytest.approx(1.0)
    assert last["F"] == 0


def test_all_cash_when_btc_below_its_average():
    h = _hourly(200, {"A": 0.01})
    btc = pd.Series(np.linspace(200, 100, 200), index=pd.date_range("2021-01-04", periods=200, freq="1D", tz="UTC"))
    w = rotation.target_weights(rotation.daily_closes(dict(h.items())), btc, sma_days=20)
    assert (w.iloc[25:] == 0).all().all()


def test_simulate_flat_prices_only_loses_fees():
    h = _hourly(30, {"A": 0.0, "B": 0.0})
    sunday = pd.Timestamp("2021-01-10", tz="UTC")
    weights = pd.DataFrame({"A": [0.25], "B": [0.25]}, index=[sunday])
    eq, orders = rotation.simulate(h, weights, fee=0.01)
    assert orders == 2
    # 50% bought (pays 1%), then sold at the end (pays 1% on the coins)
    assert eq.iloc[-1] == pytest.approx(0.5 + 0.5 * 0.99 * 0.99)


def test_decision_is_traded_on_the_next_day_not_before():
    h = _hourly(30, {"A": 0.0})
    sunday = pd.Timestamp("2021-01-10", tz="UTC")
    eq, _ = rotation.simulate(h, pd.DataFrame({"A": [0.25]}, index=[sunday]), fee=0.01)
    assert eq[eq.index < sunday + pd.Timedelta(days=1)].eq(1.0).all()
    assert eq[sunday + pd.Timedelta(days=1)] == pytest.approx(1 - 0.25 * 0.01)
