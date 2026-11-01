"""Sensitivity check for TrendEma (Phase 3). NOT candidates for live.

Each neighbour moves ONE of TrendEma's three numbers (20 / 50 / 200) by 20-25%.
If the result collapses when a number moves a little, TrendEma was lucky with
its numbers. If the neighbours stay close, the rule is robust. We do NOT switch
to the best neighbour: that would be overfitting.
"""

from pandas import DataFrame

from trend_ema import FAST_EMA, SLOW_EMA, TREND_EMA, TrendEma, ema


class _TrendEmaLengths(TrendEma):
    fast_len, slow_len, trend_len = FAST_EMA, SLOW_EMA, TREND_EMA
    startup_candle_count = 2 * 250  # enough for the longest neighbour

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema_fast"] = ema(dataframe["close"], self.fast_len)
        dataframe["ema_slow"] = ema(dataframe["close"], self.slow_len)
        dataframe["ema_trend"] = ema(dataframe["close"], self.trend_len)
        return dataframe


class EmaFast15(_TrendEmaLengths):
    fast_len = 15


class EmaFast25(_TrendEmaLengths):
    fast_len = 25


class EmaSlow40(_TrendEmaLengths):
    slow_len = 40


class EmaSlow60(_TrendEmaLengths):
    slow_len = 60


class EmaTrend150(_TrendEmaLengths):
    trend_len = 150


class EmaTrend250(_TrendEmaLengths):
    trend_len = 250


NEIGHBOURS = [EmaFast15, EmaFast25, EmaSlow40, EmaSlow60, EmaTrend150, EmaTrend250]
