"""Round 3b: market-mood filters on top of TrendEma (built on the Mac, branch mac/auto-lab).

Each class adds ONE extra entry condition to TrendEma. Exit, stoploss, position
size, protections and kill switch are unchanged.

    TrendEmaFng   skip entries when the Fear & Greed Index said "extreme greed"
                  (>= 75) YESTERDAY. Idea: buying when everyone is euphoric
                  often means buying the top. Evidence is weak (blog backtests,
                  no peer-reviewed study), so this is a real test, not a sure thing.
    TrendEmaCalm  skip entries when the coin is unusually wild right now
                  (ATR% above its own 80th percentile of the last 30 days).
                  Idea: whipsaws (fake breakouts) cluster in chaotic markets.
                  Expectation written BEFORE the test: probably little effect;
                  a 2026 study found BTC trend results did not depend on the
                  volatility regime (Tripathi, Financial Economics Letters).

Neither runs live. A class only moves to the bot after winning on train AND validation.
"""

import json
import logging
from pathlib import Path

import pandas as pd
from pandas import DataFrame

from trend_ema import TrendEma
from trend_variants import atr

logger = logging.getLogger(__name__)

FNG_FILE = Path(__file__).resolve().parent.parent / "data" / "fear_greed.json"
FNG_EXTREME_GREED = 75  # alternative.me's own label: 75-100 = "Extreme Greed"

CALM_WINDOW = 720  # 30 days of 1h candles
CALM_QUANTILE = 0.80  # "unusually wild" = wilder than 80% of the last 30 days


def load_fear_greed(path: Path = FNG_FILE) -> pd.Series:
    """{"YYYY-MM-DD": value} file -> Series indexed by UTC day. Empty if the file is missing."""
    if not path.exists():
        return pd.Series(dtype=float)
    days = json.loads(path.read_text())
    index = pd.to_datetime(list(days.keys()), utc=True)
    return pd.Series(list(days.values()), index=index, dtype=float)


def fng_for_candles(dates: pd.Series, fng: pd.Series) -> pd.Series:
    """Fear & Greed value each candle is ALLOWED to know: the one of the previous UTC day.

    Why the previous day: the value labelled "day D" is published around the
    start of day D but describes the market up to then. Using day D-1 for every
    candle of day D guarantees we never use a number that did not exist yet
    (no lookahead), at the cost of being up to ~1 day late.
    """
    yesterday = dates.dt.floor("D") - pd.Timedelta(days=1)
    return pd.Series(yesterday.map(fng).to_numpy(dtype=float), index=dates.index)


def atr_pct_is_wild(dataframe: DataFrame, window: int = CALM_WINDOW, q: float = CALM_QUANTILE) -> pd.Series:
    """True where ATR/price is above its own q-quantile of the PREVIOUS `window` candles."""
    atr_pct = atr(dataframe) / dataframe["close"]
    limit = atr_pct.shift(1).rolling(window).quantile(q)  # shift(1): today never judges itself
    return atr_pct > limit


class TrendEmaFng(TrendEma):
    """TrendEma, but no new trades the day after an 'extreme greed' reading."""

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        fng = load_fear_greed()
        if fng.empty:
            logger.warning("Fear & Greed file %s missing: filter OFF (run scripts/sentiment.py).", FNG_FILE)
        dataframe["fng"] = fng_for_candles(dataframe["date"], fng)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if "enter_long" in dataframe:
            greedy = dataframe["fng"] >= FNG_EXTREME_GREED  # NaN (no data) -> False -> allowed
            dataframe.loc[greedy, ["enter_long", "enter_tag"]] = (0, None)
        return dataframe


class TrendEmaCalm(TrendEma):
    """TrendEma, but no new trades while the coin is unusually volatile."""

    startup_candle_count = 2 * 200 + CALM_WINDOW

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["wild"] = atr_pct_is_wild(dataframe)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if "enter_long" in dataframe:
            dataframe.loc[dataframe["wild"], ["enter_long", "enter_tag"]] = (0, None)
        return dataframe
