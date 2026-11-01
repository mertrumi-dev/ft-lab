"""Tests for user_data/strategies/plateau.py (T115 grid cells)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "user_data" / "strategies"))
import plateau  # noqa: E402
import sizing  # noqa: E402
from trend_ema import ema  # noqa: E402


def test_sixteen_cells_match_the_preregistration():
    names = [plateau.cell_name(c) for c in plateau.cells()]
    assert len(names) == len(set(names)) == 16
    assert "VTG_f20_s50_t200_sl8_tv60_vw30" not in names  # today's setting = TrendEmaVolTarget itself
    rows = (ROOT / "docs" / "trials.csv").read_text()
    assert all(f",{n}," in rows for n in names)
    for n in names:
        cls = getattr(plateau, n)
        assert issubclass(cls, sizing.TrendEmaVolTarget) and plateau.cell_name(cls.cell) == n
        assert f"class {n}(" in (ROOT / "user_data" / "strategies" / "plateau.py").read_text()  # Freqtrade's text search


def test_cell_settings_reach_indicators_and_sizing():
    cls = plateau.VTG_f20_s50_t200_sl10_tv60_vw30
    assert cls.stoploss == -0.10 and cls.target_vol == 0.60 and cls.vol_window == 720
    c = plateau.VTG_f15_s60_t200_sl8_tv60_vw30
    rng = np.random.default_rng(3)
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 1500))))
    df = pd.DataFrame({"close": close, "high": close, "low": close, "volume": 1.0})
    out = c({}).populate_indicators(df.copy(), {})
    assert np.allclose(out["ema_fast"], ema(close, 15)) and np.allclose(out["ema_slow"], ema(close, 60))
    assert np.allclose(out["rvol"].dropna(), sizing.realized_vol(close, 720).dropna())
    assert plateau.VTG_f20_s50_t250_sl8_tv60_vw30.startup_candle_count == 2 * 250 + 24 * 30
    assert plateau.VTG_f20_s50_t200_sl8_tv60_vw45.startup_candle_count == 2 * 200 + 24 * 45
