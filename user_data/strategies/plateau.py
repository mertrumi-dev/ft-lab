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
    """TrendEmaVolTarget with every T115 setting as a class setting (the base keeps module constants).

    A subclass only sets `cell = (fast, slow, trend, stop %, target vol %, vol window days)`.
    The classes below are written out one by one on purpose: Freqtrade finds a strategy by
    searching the file TEXT for "class <Name>", so classes made in a loop are never found.
    """

    cell = TODAY
    fast_ema, slow_ema, trend_ema = TODAY[:3]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        fast, slow, trend, stop, tv, vw = cls.cell
        cls.fast_ema, cls.slow_ema, cls.trend_ema = fast, slow, trend
        cls.stoploss = -stop / 100
        cls.target_vol = tv / 100
        cls.vol_window = 24 * vw
        cls.startup_candle_count = 2 * trend + 24 * vw

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



class VTG_f15_s40_t200_sl8_tv60_vw30(VolTargetGrid):
    cell = (15, 40, 200, 8, 60, 30)


class VTG_f15_s50_t200_sl8_tv60_vw30(VolTargetGrid):
    cell = (15, 50, 200, 8, 60, 30)


class VTG_f15_s60_t200_sl8_tv60_vw30(VolTargetGrid):
    cell = (15, 60, 200, 8, 60, 30)


class VTG_f20_s40_t200_sl8_tv60_vw30(VolTargetGrid):
    cell = (20, 40, 200, 8, 60, 30)


class VTG_f20_s60_t200_sl8_tv60_vw30(VolTargetGrid):
    cell = (20, 60, 200, 8, 60, 30)


class VTG_f25_s40_t200_sl8_tv60_vw30(VolTargetGrid):
    cell = (25, 40, 200, 8, 60, 30)


class VTG_f25_s50_t200_sl8_tv60_vw30(VolTargetGrid):
    cell = (25, 50, 200, 8, 60, 30)


class VTG_f25_s60_t200_sl8_tv60_vw30(VolTargetGrid):
    cell = (25, 60, 200, 8, 60, 30)


class VTG_f20_s50_t150_sl8_tv60_vw30(VolTargetGrid):
    cell = (20, 50, 150, 8, 60, 30)


class VTG_f20_s50_t250_sl8_tv60_vw30(VolTargetGrid):
    cell = (20, 50, 250, 8, 60, 30)


class VTG_f20_s50_t200_sl6_tv60_vw30(VolTargetGrid):
    cell = (20, 50, 200, 6, 60, 30)


class VTG_f20_s50_t200_sl10_tv60_vw30(VolTargetGrid):
    cell = (20, 50, 200, 10, 60, 30)


class VTG_f20_s50_t200_sl8_tv50_vw30(VolTargetGrid):
    cell = (20, 50, 200, 8, 50, 30)


class VTG_f20_s50_t200_sl8_tv70_vw30(VolTargetGrid):
    cell = (20, 50, 200, 8, 70, 30)


class VTG_f20_s50_t200_sl8_tv60_vw20(VolTargetGrid):
    cell = (20, 50, 200, 8, 60, 20)


class VTG_f20_s50_t200_sl8_tv60_vw45(VolTargetGrid):
    cell = (20, 50, 200, 8, 60, 45)
