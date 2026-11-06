"""TrendEma: ft-lab's first own strategy (trend following, spot only).

Idea: buy when a short-term trend turns up inside a long-term uptrend,
sell when the short-term trend turns down.

Entry:  fast EMA crosses above slow EMA  AND  close is above the trend EMA.
Exit:   fast EMA crosses below slow EMA.

All numbers below are reasoned starting values, NOT optimized. They get
measured in Phase 1-2 (train/validation only; the final test slice stays untouched).
"""

import logging
from datetime import datetime, timedelta

import pandas as pd
from pandas import DataFrame

from freqtrade.persistence import Trade
from freqtrade.exchange import timeframe_to_minutes
from freqtrade.strategy import IStrategy

logger = logging.getLogger(__name__)


# --- Signal settings -------------------------------------------------------
FAST_EMA = 20  # ~1 day of 1h candles: short-term direction
SLOW_EMA = 50  # ~2 days: medium-term direction
TREND_EMA = 200  # ~8 days: only trade when the bigger picture is up

# --- Risk settings ---------------------------------------------------------
STOPLOSS = -0.08  # a single trade is closed at -8%
RISK_PER_TRADE = 0.01  # hitting the stoploss may cost at most 1% of capital
MAX_STAKE_RATIO = 0.25  # one trade never uses more than 25% of capital
KILL_SWITCH_DRAWDOWN = 0.20  # stop all new trades after a 20% fall from the peak
STALE_CANDLES = 2  # refuse entries if the newest candle is older than this


def ema(series: pd.Series, length: int) -> pd.Series:
    """Exponential moving average: an average that weighs recent prices more."""
    return series.ewm(span=length, adjust=False).mean()


def crossed_above(a: pd.Series, b: pd.Series) -> pd.Series:
    """True on the candle where `a` moves from <= b to > b."""
    return (a > b) & (a.shift(1) <= b.shift(1))


def crossed_below(a: pd.Series, b: pd.Series) -> pd.Series:
    """True on the candle where `a` moves from >= b to < b."""
    return (a < b) & (a.shift(1) >= b.shift(1))


def risk_based_stake(capital: float, risk_per_trade: float, stoploss: float, max_ratio: float) -> float:
    """How much to put into one trade so that hitting the stoploss loses `risk_per_trade`.

    Example: capital 1000, risk 1%, stoploss -8%  ->  1000 * 0.01 / 0.08 = 125.
    Capped at `max_ratio` of capital.
    """
    stake = capital * risk_per_trade / abs(stoploss)
    return min(stake, capital * max_ratio)


def drawdown_from_peak(starting: float, closed_profits: list[float]) -> float:
    """Current fall of realized equity from its highest point, as a ratio (0.2 = 20%).

    `closed_profits` must be in the order the trades were closed.
    """
    equity = peak = starting
    for profit in closed_profits:
        equity += profit
        peak = max(peak, equity)
    return (peak - equity) / peak if peak > 0 else 0.0


def worst_drawdown(starting: float, closed_profits: list[float]) -> float:
    """The LARGEST fall of realized equity from a previous peak, over the whole history.

    The kill switch uses this, not the current fall: once realized equity has been 20% below
    its peak, entries stay blocked even if trades that were still open later close with a profit
    and pull the current fall back under 20% (R13: "until a human looks"). Found by the
    kill-switch drill (docs/research/08). Still computed from the trade history only, so a
    restart cannot reset it; a human resets it by starting a new database.
    """
    equity = peak = starting
    worst = 0.0
    for profit in closed_profits:
        equity += profit
        peak = max(peak, equity)
        worst = max(worst, (peak - equity) / peak if peak > 0 else 0.0)
    return worst


class TrendEma(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "1h"
    can_short = False  # spot only: we can only profit when price goes up

    # EMA200 needs a long warm-up before its values are reliable.
    startup_candle_count: int = 2 * TREND_EMA

    # Trend following lets winners run: no fixed take-profit target.
    minimal_roi = {"0": 100}

    # Hard safety net: sell if a trade is 8% down, whatever the EMAs say.
    stoploss = STOPLOSS
    trailing_stop = False

    use_exit_signal = True
    exit_profit_only = False
    process_only_new_candles = True

    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }

    @property
    def protections(self):
        # Counts are in candles; 1 candle = 1 hour.
        return [
            {
                # After closing a trade on a pair, wait 2 hours before re-entering it.
                "method": "CooldownPeriod",
                "stop_duration_candles": 2,
            },
            {
                # 3 stoplosses (any pair) within 24h -> no new trades for 12h.
                "method": "StoplossGuard",
                "lookback_period_candles": 24,
                "trade_limit": 3,
                "stop_duration_candles": 12,
                "only_per_pair": False,
            },
        ]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema_fast"] = ema(dataframe["close"], FAST_EMA)
        dataframe["ema_slow"] = ema(dataframe["close"], SLOW_EMA)
        dataframe["ema_trend"] = ema(dataframe["close"], TREND_EMA)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            crossed_above(dataframe["ema_fast"], dataframe["ema_slow"])
            & (dataframe["close"] > dataframe["ema_trend"])
            & (dataframe["volume"] > 0),
            ["enter_long", "enter_tag"],
        ] = (1, "ema_cross_up")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            crossed_below(dataframe["ema_fast"], dataframe["ema_slow"])
            & (dataframe["volume"] > 0),
            ["exit_long", "exit_tag"],
        ] = (1, "ema_cross_down")
        return dataframe

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
        # Total capital = free cash + money in open trades.
        capital = self.wallets.get_total_stake_amount()
        stake = risk_based_stake(capital, RISK_PER_TRADE, self.stoploss, MAX_STAKE_RATIO)
        return min(stake, max_stake)

    def kill_switch_active(self) -> bool:
        """The kill switch can be switched off ONLY in a backtest, for research.

        Why: in a backtest the switch stops all buying forever once it fires, so
        the rest of the period says nothing about the rule. To judge the rule we
        sometimes run it without the switch (config research-no-kill-switch.json).
        In dry-run or live it is always on, whatever the config says.
        """
        if not self.config.get("ftlab_research_no_kill_switch", False):
            return True
        runmode = getattr(getattr(self, "dp", None), "runmode", None)
        return getattr(runmode, "value", None) not in ("backtest", "hyperopt")

    def confirm_trade_entry(
        self,
        pair: str,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time: datetime,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> bool:
        # Kill switch: realized equity fell 20% from its peak -> no new trades.
        # It is computed from the trade history, so a restart does not reset it;
        # only a human starting a new database can; the research no-kill-switch config works only in backtest (see kill_switch_active).
        if self.kill_switch_active():
            closed = sorted(
                Trade.get_trades_proxy(is_open=False), key=lambda t: t.close_date_utc
            )
            drawdown = worst_drawdown(
                self.wallets.get_starting_balance(), [t.close_profit_abs or 0.0 for t in closed]
            )
            if drawdown >= KILL_SWITCH_DRAWDOWN:
                logger.warning(
                    "KILL SWITCH: realized drawdown reached %.1f%% (>= %.0f%%) since the start. Entry on %s refused.",
                    drawdown * 100,
                    KILL_SWITCH_DRAWDOWN * 100,
                    pair,
                )
                return False

        # Stale data guard: don't trade on old prices (exchange/network problem).
        if self.dp.runmode.value in ("live", "dry_run"):
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            if dataframe.empty:
                logger.warning("No data for %s, entry refused.", pair)
                return False
            max_age = timedelta(minutes=timeframe_to_minutes(self.timeframe) * STALE_CANDLES)
            last_candle = dataframe["date"].iloc[-1].to_pydatetime()
            if current_time - last_candle > max_age:
                logger.warning("Stale data for %s (last candle %s), entry refused.", pair, last_candle)
                return False

        return True
