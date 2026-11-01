"""Phase 2, family 2: buy short dips inside an uptrend (mean reversion), RSI + ATR.

Idea source: Larry Connors & Cesar Alvarez, "Short Term Trading Strategies That
Work" (2008), the "RSI(2)" rules, published for stock indices on daily candles:
    price above its 200 average  AND  2-period RSI below 10  -> buy
    price closes above its 5 average                         -> sell
Only the idea is used; the code below is ft-lab's own. Connors used no stop;
we add an ATR stop because crypto can fall far faster than an index.

Why test it at all: TrendEma buys strength. This buys weakness. If both work,
they earn at different moments, which smooths the equity curve.
Honest prior: published tests say it works on stock indices; on crypto the
evidence is thin and fees (0.15% per side here) eat small mean-reversion gains.

Numbers are Connors' textbook values, NOT optimized.
"""

from datetime import datetime

import pandas as pd
from pandas import DataFrame

from freqtrade.persistence import Trade
from freqtrade.strategy import stoploss_from_absolute
from trend_ema import ema
from trend_variants import TrendEmaAtr, atr

RSI_LENGTH = 2  # very short RSI: reacts to 2-3 down candles in a row
RSI_ENTRY = 10  # "oversold": the last candles fell unusually hard
EXIT_SMA = 5  # sell once price closes back above its 5-candle average
TREND_LEN = 200  # only buy dips while the bigger trend is up
DIP_ATR_MULT = 2.5  # stop = entry price - 2.5 x ATR, never wider than -8%


def rsi(close: pd.Series, length: int) -> pd.Series:
    """Relative Strength Index (0-100), Wilder's smoothing.

    Compares average up-moves with average down-moves. Near 0 = almost only
    falls lately, near 100 = almost only rises. With length 2 it looks at
    roughly the last 2-3 candles.
    """
    change = close.diff()
    gain = change.clip(lower=0).ewm(alpha=1 / length, adjust=False).mean()
    loss = (-change.clip(upper=0)).ewm(alpha=1 / length, adjust=False).mean()
    # loss == 0 means no falls at all -> RSI 100.
    rs = gain / loss.where(loss > 0)
    return (100 - 100 / (1 + rs)).fillna(100.0).where(change.notna())


def dip_stop_price(open_rate: float, atr_value: float, mult: float, cap: float) -> float:
    """Fixed stop below the entry price: mult x ATR, at most `cap` (0.08 = 8%) away."""
    distance = min(mult * atr_value, cap * open_rate)
    return open_rate - distance


class DipRsi(TrendEmaAtr):
    """Buy a sharp short dip above the trend EMA; sell on the bounce. 1h candles.

    Inherits from TrendEmaAtr: 1% risk sizing from the ATR stop distance,
    the 25% cap, the kill switch and the protections stay identical.
    """

    atr_mult = DIP_ATR_MULT
    startup_candle_count: int = 2 * TREND_LEN

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema_trend"] = ema(dataframe["close"], TREND_LEN)
        dataframe["rsi"] = rsi(dataframe["close"], RSI_LENGTH)
        dataframe["sma_exit"] = dataframe["close"].rolling(EXIT_SMA).mean()
        dataframe["atr"] = atr(dataframe)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["close"] > dataframe["ema_trend"])
            & (dataframe["rsi"] < RSI_ENTRY)
            & (dataframe["volume"] > 0),
            ["enter_long", "enter_tag"],
        ] = (1, "rsi_dip")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["close"] > dataframe["sma_exit"]) & (dataframe["volume"] > 0),
            ["exit_long", "exit_tag"],
        ] = (1, "bounce")
        return dataframe

    def custom_stoploss(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        after_fill: bool,
        **kwargs,
    ) -> float | None:
        candle = self._last_candle(pair)
        if candle is None or not candle["atr"] > 0:
            return None  # keep the -8% hard stop
        # Anchored at the ENTRY price, not the latest close: a dip trade is
        # short, so we do not trail. (Freqtrade never moves a stop down anyway.)
        stop_price = dip_stop_price(trade.open_rate, candle["atr"], self.atr_mult, abs(self.stoploss))
        return stoploss_from_absolute(stop_price, current_rate)


class DipRsi4h(DipRsi):
    """Same rules on 4h candles: 4x fewer signals, bigger moves per trade, so fees matter less."""

    timeframe = "4h"
