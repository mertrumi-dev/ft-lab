"""Experimental variants of TrendEma, built from docs/research/01 and 02.

Each class changes ONE thing compared to TrendEma, so a backtest tells us
exactly what that one change did. All of them keep TrendEma's risk rules
(1% risk per trade, -8% hard stop cap, protections, kill switch).

    TrendEmaAtr       stop follows volatility (ATR) and trails up; EMA exit kept
    TrendEmaAtrTrail  same stop, but the trailing stop is the ONLY exit
    TrendEma4h        TrendEma on 4-hour candles (fewer trades, less fee)
    TrendBreakout     entry = price breaks its 20-candle high (Turtle style)

Round 2 (after the first train results, docs/results.md):

    TrendEmaAtrWide   ATR stop at 5 x ATR (2.5 x was too tight on 1h candles)
    TrendEmaSlow      slower averages: EMA50/200, trend filter EMA600
    TrendEmaMulti     3 averages pairs vote; buy when 2 of 3 say "up"
    TrendEmaBtc       only buy when Bitcoin itself is above its EMA200

Round 3 (after the year-by-year view):

    TrendEmaAdx       only buy when the trend is strong (ADX > 20)
    TrendEmaLongTrend only buy when price is above its ~6-week average too

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
    ema,
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
    atr_mult = ATR_STOP_MULT

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
            distance = atr_stop_distance(candle["close"], candle["atr"], self.atr_mult, abs(STOPLOSS))
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
        stop_price = candle["close"] - self.atr_mult * candle["atr"]
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


# --- Round 2 ----------------------------------------------------------------


class TrendEmaAtrWide(TrendEmaAtr):
    """Same as TrendEmaAtr with a wider stop; round 1 showed 2.5 x ATR stops out on noise."""

    atr_mult = 5.0


class TrendEmaSlow(TrendEma):
    """Slower averages: fewer, longer trades (research 02: longer windows worked better on BTC)."""

    fast_len, slow_len, trend_len = 50, 200, 600
    startup_candle_count = 1500  # >= 2 x the longest average in this class and its neighbours

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema_fast"] = ema(dataframe["close"], self.fast_len)
        dataframe["ema_slow"] = ema(dataframe["close"], self.slow_len)
        dataframe["ema_trend"] = ema(dataframe["close"], self.trend_len)
        return dataframe


# --- Sensitivity check for TrendEmaSlow (Phase 3 idea, train slice only) ------
# Each neighbour moves ONE number by ~25%. If the result collapses when a number
# moves a little, TrendEmaSlow was lucky with its numbers (overfit). If the
# neighbours stay close, the rule is robust. These are NOT candidates for live.


class SlowFast40(TrendEmaSlow):
    fast_len = 40


class SlowFast60(TrendEmaSlow):
    fast_len = 60


class SlowSlow150(TrendEmaSlow):
    slow_len = 150


class SlowSlow250(TrendEmaSlow):
    slow_len = 250


class SlowTrend450(TrendEmaSlow):
    trend_len = 450


class SlowTrend750(TrendEmaSlow):
    trend_len = 750


SLOW_NEIGHBOURS = [SlowFast40, SlowFast60, SlowSlow150, SlowSlow250, SlowTrend450, SlowTrend750]


MULTI_PAIRS = [(20, 50), (50, 150), (100, 300)]


class TrendEmaMulti(TrendEma):
    """Three fast/slow pairs vote. Less dependent on one choice of numbers (research 02)."""

    startup_candle_count = 600

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)  # keeps ema_trend (200)
        votes = sum(
            (ema(dataframe["close"], fast) > ema(dataframe["close"], slow)).astype(int)
            for fast, slow in MULTI_PAIRS
        )
        dataframe["votes"] = votes
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        bull = dataframe["votes"] >= 2
        dataframe.loc[
            bull & ~bull.shift(1, fill_value=False)
            & (dataframe["close"] > dataframe["ema_trend"])
            & (dataframe["volume"] > 0),
            ["enter_long", "enter_tag"],
        ] = (1, "votes_up")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        bull = dataframe["votes"] >= 2
        dataframe.loc[
            ~bull & bull.shift(1, fill_value=False) & (dataframe["volume"] > 0),
            ["exit_long", "exit_tag"],
        ] = (1, "votes_down")
        return dataframe


class TrendEmaBtc(TrendEma):
    """Market filter: altcoins usually fall with Bitcoin, so only buy when BTC is in an uptrend."""

    def informative_pairs(self):
        return [("BTC/USDT", self.timeframe)]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["btc_bull"] = True
        dp = getattr(self, "dp", None)  # set by Freqtrade; missing in plain unit tests
        if dp is not None:
            btc = dp.get_pair_dataframe("BTC/USDT", self.timeframe)
            if not btc.empty:
                btc = btc[["date", "close"]].copy()
                btc["btc_bull"] = btc["close"] > ema(btc["close"], 200)
                merged = dataframe[["date"]].merge(btc[["date", "btc_bull"]], on="date", how="left")
                dataframe["btc_bull"] = merged["btc_bull"].fillna(False).astype(bool).to_numpy()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if "enter_long" in dataframe:
            dataframe.loc[~dataframe["btc_bull"], ["enter_long", "enter_tag"]] = (0, None)
        return dataframe


# --- Round 3: "read the chart better" filters (2026-11-01) -------------------
# Each adds ONE extra condition to TrendEma's entry. Exit and risk unchanged.

ADX_LENGTH = 14
ADX_MIN = 20  # common textbook threshold: below 20 = no real trend
LONG_TREND_EMA = 1000  # ~42 days of 1h candles, roughly a daily EMA42


def adx(dataframe: DataFrame, length: int = ADX_LENGTH) -> pd.Series:
    """Average Directional Index: how STRONG the trend is (0-100), not its direction.

    +DM = how much today's high is above yesterday's high (if that is the bigger move)
    -DM = how much today's low is below yesterday's low (if that is the bigger move)
    Both are divided by ATR, smoothed (Wilder), and ADX is the smoothed
    |+DI - -DI| / (+DI + -DI). High ADX = price is moving clearly one way.
    """
    up = dataframe["high"].diff()
    down = -dataframe["low"].diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    alpha = 1 / length
    atr_ = atr(dataframe, length)
    plus_di = 100 * plus_dm.ewm(alpha=alpha, adjust=False).mean() / atr_
    minus_di = 100 * minus_dm.ewm(alpha=alpha, adjust=False).mean() / atr_
    total = (plus_di + minus_di).replace(0, float("nan"))
    dx = 100 * (plus_di - minus_di).abs() / total
    return dx.ewm(alpha=alpha, adjust=False).mean()


class TrendEmaAdx(TrendEma):
    """Only buy when the trend is strong (ADX > 20): skips sideways, choppy markets."""

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["adx"] = adx(dataframe)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if "enter_long" in dataframe:
            weak = ~(dataframe["adx"] > ADX_MIN)
            dataframe.loc[weak, ["enter_long", "enter_tag"]] = (0, None)
        return dataframe


class TrendEmaLongTrend(TrendEma):
    """Only buy when price is also above a ~6-week average: the coin's own big-picture trend."""

    startup_candle_count = 2000

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["ema_long"] = ema(dataframe["close"], LONG_TREND_EMA)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if "enter_long" in dataframe:
            below = ~(dataframe["close"] > dataframe["ema_long"])
            dataframe.loc[below, ["enter_long", "enter_tag"]] = (0, None)
        return dataframe


# --- Round 5: exits (2026-11-01) ---------------------------------------------
# Diagnosis after 22 trials: entry filters only push more money into cash.
# The bot holds coins ~17% of the time and misses most of each rise. Hypothesis:
# exit later, not enter differently.


class TrendEmaHold(TrendEma):
    """Same entry. Exit only when the close crosses below the trend line (EMA200)
    instead of when EMA20 crosses below EMA50. No new number: reuses the filter line.
    The -8% hard stop still protects every trade."""

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        below = dataframe["close"] < dataframe["ema_trend"]
        dataframe.loc[
            below & ~below.shift(1, fill_value=False) & (dataframe["volume"] > 0),
            ["exit_long", "exit_tag"],
        ] = (1, "below_trend")
        return dataframe


# --- Round 7: fight whipsaw (from the trade analysis, docs/results.md) -------
# 443 of 638 trades closed within 3 days, nearly all at a loss: the EMAs cross
# back soon after entry. Two independent fixes, numbers chosen before testing.
EXIT_CONFIRM_CANDLES = 3  # the cross-down must still hold after 3 hours
SLOPE_LOOKBACK = 24  # EMA50 must be higher than 24 hours (1 day) ago


class TrendEmaExitConfirm(TrendEma):
    """Same entry. Sell only when EMA20 has stayed below EMA50 for 3 candles in a row.

    A short dip that crosses back within 3 hours no longer sells the coin.
    The -8% stop still protects every trade."""

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        below = (dataframe["ema_fast"] < dataframe["ema_slow"]).astype(int)
        held = below.rolling(EXIT_CONFIRM_CANDLES).sum() == EXIT_CONFIRM_CANDLES
        dataframe.loc[
            held & ~held.shift(1, fill_value=False) & (dataframe["volume"] > 0),
            ["exit_long", "exit_tag"],
        ] = (1, "ema_cross_down_confirmed")
        return dataframe


class TrendEmaSlope(TrendEma):
    """Same exit. Buy the cross-up only if EMA50 itself is rising (higher than 1 day ago).

    A cross-up while the medium trend is still falling is often a bounce, not a trend."""

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        falling = dataframe["ema_slow"] <= dataframe["ema_slow"].shift(SLOPE_LOOKBACK)
        dataframe.loc[falling, ["enter_long", "enter_tag"]] = (0, None)
        return dataframe


ENTRY_CONFIRM_CANDLES = 3  # the cross-up must still hold after 3 hours


class TrendEmaEntryConfirm(TrendEma):
    """Same exit. Buy only when EMA20 has stayed above EMA50 for 3 candles in a row
    (on that 3rd candle, once per streak), with the close above EMA200.

    A cross-up that falls back within 3 hours is never bought, so fewer whipsaw trades."""

    confirm_candles = ENTRY_CONFIRM_CANDLES

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        n = self.confirm_candles
        above = (dataframe["ema_fast"] > dataframe["ema_slow"]).astype(int)
        held = above.rolling(n).sum() == n
        dataframe.loc[
            held & ~held.shift(1, fill_value=False)
            & (dataframe["close"] > dataframe["ema_trend"])
            & (dataframe["volume"] > 0),
            ["enter_long", "enter_tag"],
        ] = (1, f"ema_cross_up_{n}h")
        return dataframe


class EntryConfirm2(TrendEmaEntryConfirm):
    """Sensitivity neighbour: 2 candles (not a candidate)."""

    confirm_candles = 2


class EntryConfirm4(TrendEmaEntryConfirm):
    """Sensitivity neighbour: 4 candles (not a candidate)."""

    confirm_candles = 4
