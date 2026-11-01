import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import tsmom  # noqa: E402


def _daily(series: dict, start="2021-01-01"):
    n = len(next(iter(series.values())))
    idx = pd.date_range(start, periods=n, freq="1D", tz="UTC")
    return pd.DataFrame(series, index=idx)


def test_rising_coin_is_held_falling_coin_is_not():
    rng = np.random.default_rng(0)
    noise = 1 + rng.normal(0, 0.01, 120)
    up = 100 * np.cumprod(noise * 1.01)
    down = 100 * np.cumprod(noise * 0.99)
    w = tsmom.target_weights(_daily({"UP": up, "DOWN": down}))
    held = w.ffill().fillna(0.0).iloc[-1]
    assert held["UP"] > 0
    assert held["DOWN"] == 0


def test_size_is_capped_by_volatility_part_and_r4():
    rng = np.random.default_rng(1)
    calm = 100 * np.cumprod(1.002 + rng.normal(0, 0.005, 120))  # ~10% vol -> full part
    wild = 100 * np.cumprod(np.tile([1.15, 0.89], 60))  # rising, ~250% vol -> small share
    w = tsmom.target_weights(_daily({"CALM": calm, "WILD": wild})).ffill().fillna(0.0).iloc[-1]
    assert w["CALM"] == pytest.approx(0.25)  # 1/2 part capped at 25% (R4)
    assert 0 < w["WILD"] < 0.25 / 2


def test_no_lookahead_decision_is_traded_next_day():
    idx = pd.date_range("2021-01-01", periods=24 * 5, freq="1h", tz="UTC")
    hourly = pd.DataFrame({"A": 100.0}, index=idx)
    day = pd.Timestamp("2021-01-02", tz="UTC")
    eq, orders = tsmom.simulate(hourly, pd.DataFrame({"A": [0.5]}, index=[day]), fee=0.01)
    assert orders == 1
    assert eq[eq.index < day + pd.Timedelta(days=1)].eq(1.0).all()
    assert eq[day + pd.Timedelta(days=1)] == pytest.approx(1 - 0.5 * 0.01)


def test_nan_means_leave_the_coin_alone():
    idx = pd.date_range("2021-01-01", periods=24 * 5, freq="1h", tz="UTC")
    hourly = pd.DataFrame({"A": 100.0, "B": 100.0}, index=idx)
    d1, d2 = pd.Timestamp("2021-01-01", tz="UTC"), pd.Timestamp("2021-01-02", tz="UTC")
    w = pd.DataFrame({"A": [0.25, np.nan], "B": [np.nan, 0.25]}, index=[d1, d2])
    _, orders = tsmom.simulate(hourly, w, fee=0.0)
    assert orders == 2  # A bought once, B bought once, A not re-traded on day 2
