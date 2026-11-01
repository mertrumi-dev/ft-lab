"""T115: the VolTarget plateau map (docs/journal.md, pre-registered 2026-11-01 23:25 UTC).

One class per grid cell, all TrendEmaVolTarget with one or two settings moved:
  VTG_f{fast}_s{slow}_t{trend}_sl{stop %}_tv{target vol %}_vw{vol window days}
Train core only. The selection rule (plateau centre = highest neighbourhood MEDIAN Calmar,
never the single best cell) is fixed in the journal before any cell ran.
"""

import sys
from pathlib import Path

from pandas import DataFrame

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sizing import TrendEmaVolTarget  # noqa: E402
from trend_ema import ema  # noqa: E402

TODAY = (20, 50, 200, 8, 60, 30)  # fast, slow, trend, stop %, target vol %, vol window days


class VolTargetGrid(TrendEmaVolTarget):
    """TrendEmaVolTarget with the EMA lengths as class settings (the base keeps module constants)."""

    fast_ema = 20
    slow_ema = 50
    trend_ema = 200

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["ema_fast"] = ema(dataframe["close"], self.fast_ema)
        dataframe["ema_slow"] = ema(dataframe["close"], self.slow_ema)
        dataframe["ema_trend"] = ema(dataframe["close"], self.trend_ema)
        return dataframe


def cells() -> list[tuple[int, int, int, int, int, int]]:
    """The 16 pre-registered cells: fast x slow 3x3 (8 new) + one-at-a-time for the other four (8)."""
    f, s, t, sl, tv, vw = TODAY
    out = [(ff, ss, t, sl, tv, vw) for ff in (15, 20, 25) for ss in (40, 50, 60) if (ff, ss) != (f, s)]
    out += [(f, s, x, sl, tv, vw) for x in (150, 250)]
    out += [(f, s, t, x, tv, vw) for x in (6, 10)]
    out += [(f, s, t, sl, x, vw) for x in (50, 70)]
    out += [(f, s, t, sl, tv, x) for x in (20, 45)]
    return out


def cell_name(c: tuple[int, ...]) -> str:
    return "VTG_f%d_s%d_t%d_sl%d_tv%d_vw%d" % c


def make_cell(c: tuple[int, int, int, int, int, int]) -> type:
    fast, slow, trend, stop, tv, vw = c
    attrs = {
        "__module__": __name__,  # Freqtrade only loads classes whose module is this file
        "fast_ema": fast, "slow_ema": slow, "trend_ema": trend,
        "stoploss": -stop / 100, "target_vol": tv / 100, "vol_window": 24 * vw,
        "startup_candle_count": 2 * trend + 24 * vw,
    }  # fmt: skip
    return type(cell_name(c), (VolTargetGrid,), attrs)


for _c in cells():
    globals()[cell_name(_c)] = make_cell(_c)
