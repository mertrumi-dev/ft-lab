import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import chart  # noqa: E402
import ft  # noqa: E402


def _daily(closes):
    idx = pd.date_range("2025-01-01", periods=len(closes), freq="1D", tz="UTC")
    return pd.DataFrame({"close": closes, "volume": 1.0}, index=idx)


def test_reading_of_a_steady_uptrend():
    d = _daily(list(np.linspace(100, 200, 300)))
    r = chart.daily_reading(d)
    assert r["close"] == 200
    assert r["vs_ema20"] > 0 and r["vs_ema200"] > 0
    assert r["ret7"] > 0 and r["high60"] == 200


def test_support_and_resistance_are_swing_points_around_the_price():
    closes = [100, 90, 80, 90, 100, 110, 120, 110, 100, 95, 100] * 6
    r = chart.daily_reading(_daily(closes))
    assert r["support"] is not None and r["support"] < r["close"]
    assert r["resistance"] is not None and r["resistance"] > r["close"]


def test_bot_view_entry_only_on_the_cross_above_trend():
    n = 24 * 40
    c = np.concatenate([np.linspace(100, 120, n - 30), np.linspace(120, 117, 25), np.linspace(117, 125, 5)])
    h = pd.DataFrame({"close": c}, index=pd.date_range("2025-01-01", periods=n, freq="1h", tz="UTC"))
    b = chart.bot_view(h)
    assert b["above_trend"]
    assert 0 < b["size_scale"] <= 1


def test_ft_chart_downloads_the_pair_then_reads_it():
    cmds = ft.build_commands(ft.parse_args(["chart", "--pair", "link"]))
    assert "LINK/USDT" in cmds[0] and "download-data" in cmds[0]
    assert cmds[1][-2:] == ["--pair", "LINK/USDT"]
