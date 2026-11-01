"""TrendDonchianEnsemble: daily trend following with 9 channel lengths voting.

Idea source (our own code, no code copied): Zarattini, Pagani, Barbon (2025),
"Catching Crypto Trends: A Tactical Approach for Bitcoin and Altcoins",
https://concretumgroup.com/catching-crypto-trends-a-tactical-approach-for-bitcoin-and-altcoins/

What we take from the paper:
  * daily candles
  * Donchian channel: highest high / lowest low of the last N days
  * per length N: go long when the close breaks above the N-day high; exit when
    the close falls below a stop that sits at the channel middle and only moves up
  * 9 lengths (5 ... 360 days) vote; position size = share of lengths that are long
  * volatility targeting: smaller position when the coin is wild (25% yearly target)

What we do differently (our risk rules, docs/risk-rules.md):
  * no leverage: size never above what the 1% risk rule allows (12.5% of capital
    per coin with the -8% hard stop); the paper allows up to 200%
  * the -8% hard stop, protections and the kill switch from TrendEma stay
"""

import math
from datetime import datetime

import numpy as np
import pandas as pd
from pandas import DataFrame

from freqtrade.persistence import Trade
from trend_ema import MAX_STAKE_RATIO, RISK_PER_TRADE, STOPLOSS, TrendEma, risk_based_stake

LOOKBACKS = [5, 10, 20, 30, 60, 90, 150, 250, 360]
TARGET_VOL = 0.25  # yearly volatility target from the paper
VOL_WINDOW = 90  # days used to measure volatility
REBALANCE_BAND = 0.20  # only resize when off target by more than 20% (paper)


def channel_state(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int) -> np.ndarray:
    """1 where the N-day channel system is long, else 0. Uses only PAST candles.

    upper/lower = highest high / lowest low of the previous n candles (not today).
    Enter: close > upper. Exit: close < stop, stop = channel middle, never lowered.
    """
    h = pd.Series(high).rolling(n).max().shift(1).to_numpy()
    lo = pd.Series(low).rolling(n).min().shift(1).to_numpy()
    mid = (h + lo) / 2
    state = np.zeros(len(close))
    in_pos, stop = False, -math.inf
    for i in range(len(close)):
        if np.isnan(h[i]):
            continue
        if in_pos:
            stop = max(stop, mid[i])
            if close[i] < stop:
                in_pos = False
        elif close[i] > h[i]:
            in_pos, stop = True, mid[i]
        state[i] = 1.0 if in_pos else 0.0
    return state


def target_fraction(ensemble: float, yearly_vol: float) -> float:
    """Share of the per-coin budget to hold: votes x volatility scaling (never above 1)."""
    if not ensemble > 0 or not yearly_vol > 0:
        return 0.0
    return float(ensemble * min(1.0, TARGET_VOL / yearly_vol))


class TrendDonchianEnsemble(TrendEma):
    timeframe = "1d"
    startup_candle_count = 400  # longest channel 360 days + volatility window
    position_adjustment_enable = True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        h, lo, c = (dataframe[k].to_numpy(dtype=float) for k in ("high", "low", "close"))
        states = [channel_state(h, lo, c, n) for n in LOOKBACKS]
        dataframe["ensemble"] = np.mean(states, axis=0)
        returns = dataframe["close"].pct_change()
        dataframe["vol_yearly"] = returns.rolling(VOL_WINDOW).std() * math.sqrt(365)
        dataframe["target"] = [
            target_fraction(e, v) for e, v in zip(dataframe["ensemble"], dataframe["vol_yearly"])
        ]
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["target"] > 0) & (dataframe["volume"] > 0), ["enter_long", "enter_tag"]
        ] = (1, "ensemble_on")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["ensemble"] == 0) & (dataframe["volume"] > 0), ["exit_long", "exit_tag"]
        ] = (1, "ensemble_off")
        return dataframe

    # --- sizing --------------------------------------------------------------

    def _budget(self) -> float:
        """Most money one coin may hold under the 1% risk rule (-8% stop -> 12.5%)."""
        capital = self.wallets.get_total_stake_amount()
        return risk_based_stake(capital, RISK_PER_TRADE, STOPLOSS, MAX_STAKE_RATIO)

    def _target(self, pair: str) -> float:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or dataframe.empty:
            return 0.0
        return float(dataframe["target"].iloc[-1])

    def custom_stake_amount(
        self, pair: str, current_time: datetime, current_rate: float, proposed_stake: float,
        min_stake: float | None, max_stake: float, leverage: float, entry_tag: str | None,
        side: str, **kwargs,
    ) -> float:  # fmt: skip
        return min(self._budget() * self._target(pair), max_stake)

    def adjust_trade_position(
        self, trade: Trade, current_time: datetime, current_rate: float, current_profit: float,
        min_stake: float | None, max_stake: float, current_entry_rate: float,
        current_exit_rate: float, current_entry_profit: float, current_exit_profit: float,
        **kwargs,
    ) -> float | None:  # fmt: skip
        target = self._budget() * self._target(trade.pair)
        if target <= 0:
            return None  # the exit signal closes the trade
        held = trade.amount * current_rate
        diff = target - held
        if abs(diff) < REBALANCE_BAND * target:
            return None
        if diff > 0:
            return min(diff, max_stake) if (min_stake is None or diff >= min_stake) else None
        if min_stake is not None and -diff < min_stake:
            return None
        return max(diff, -held)  # partial sell, never more than we hold
