"""Experimental variants of TrendEma, built from docs/research/01 and 02.

Each class changes ONE thing compared to TrendEma, so a backtest tells us
exactly what that one change did. All of them keep TrendEma's risk rules
(1% risk per trade, -8% hard stop cap, protections, kill switch).

    TrendEmaAtr       stop follows volatility (ATR) and trails up; EMA exit kept
    TrendEmaAtrTrail  same stop, but the trailing stop is the ONLY exit
    TrendEma4h        TrendEma on 4-hour candles (fewer trades, less fee)
    TrendBreakout     entry = price breaks its 20-candle high (Turtle style)

None of these run live. The live bot stays on TrendEma until a variant wins
on the train AND validation slices.
"""

from datetime import datetime

import pandas as pd
from pandas import DataFrame

from freqtrade.persistence import Trade
from freqtrade.strategy import stoploss_from_absolute
from trend_ema import (
    MAX_STAKE_RATIO,
    RISK_PER_TRADE,
    STOPLOSS,
    TrendEma,
    risk_based_stake,
)

ATR_LENGTH = 14  # standard ATR window
ATR_STOP_MULT = 2.5  # stop = price - 2.5 x ATR (Turtles used 2; research tested 2-3.5)
BREAKOUT_LENGTH = 20  # Turtle "System 1" entry window


def atr(dataframe: DataFrame, length: int = ATR_LENGTH) -> pd.Series:
    """Average True Range: how much one candle typically moves, in price units.

    True range = the largest of: high-low, |high - previous close|, |low - previous close|.
    Averaged with Wilder's smoothing (an EMA with alpha = 1/length).
    """
    prev_close = dataframe["close"].shift(1)
    true_range = pd.concat(
        [
            dataframe["high"] - dataframe["low"],
            (dataframe["high"] - prev_close).abs(),
            (dataframe["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / length, adjust=False).mean()


def atr_stop_distance(close: float, atr_value: float, mult: float, cap: float) -> float:
    """Stop distance as a ratio of price, never wider than `cap` (e.g. 0.08)."""
    return min(mult * atr_value / close, cap)


class TrendEmaAtr(TrendEma):
    """Volatility-based trailing stop. Calm coin -> tight stop, wild coin -> wide stop."""

    use_custom_stoploss = True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["atr"] = atr(dataframe)
        return dataframe

    def _last_candle(self, pair: str) -> pd.Series | None:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or dataframe.empty:
            return None
        return dataframe.iloc[-1]

    def custom_stake_amount(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_stake: float,
        min_stake: float | None,
        max_stake: float,
        leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        # Same 1% risk rule, but the stop distance comes from ATR, so the
        # position is smaller on wild coins and bigger on calm ones.
        candle = self._last_candle(pair)
        distance = abs(STOPLOSS)
        if candle is not None and candle["atr"] > 0:
            distance = atr_stop_distance(candle["close"], candle["atr"], ATR_STOP_MULT, abs(STOPLOSS))
        capital = self.wallets.get_total_stake_amount()
        stake = risk_based_stake(capital, RISK_PER_TRADE, -distance, MAX_STAKE_RATIO)
        return min(stake, max_stake)

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
        # Stop price follows the latest close. Freqtrade never moves a stop down,
        # so this trails upward as the price rises and locks in profit.
        stop_price = candle["close"] - ATR_STOP_MULT * candle["atr"]
        return stoploss_from_absolute(stop_price, current_rate)


class TrendEmaAtrTrail(TrendEmaAtr):
    """Let winners run: no EMA exit, the trailing ATR stop decides when to sell."""

    use_exit_signal = False


class TrendEma4h(TrendEma):
    """Same rules on 4-hour candles. Protection windows count candles, so they get 4x longer."""

    timeframe = "4h"


class TrendBreakout(TrendEma):
    """Buy when price closes above the highest high of the previous 20 candles, in an uptrend."""

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        # shift(1): compare with the PREVIOUS 20 candles, never the current one (no peeking).
        dataframe["high_n"] = dataframe["high"].rolling(BREAKOUT_LENGTH).max().shift(1)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["close"] > dataframe["high_n"])
            & (dataframe["close"] > dataframe["ema_trend"])
            & (dataframe["volume"] > 0),
            ["enter_long", "enter_tag"],
        ] = (1, "breakout_20")
        return dataframe
