"""Round 11: market regime gate from BTC's DAILY trend.

Where it came from (train-only analysis of TrendEma's 638 train trades,
2026-11-01, no validation or test data read): trades opened while BTC's daily
SMA50 was RISING (vs 10 days earlier) made +2,837 USDT over 376 trades; trades
opened while it was FALLING lost -294 USDT over 262 trades. BTC above/below
SMA200, volatility and choppiness splits showed no clear pattern.

    TrendEmaBtcRising  TrendEma, but new entries only while BTC's daily SMA50
                       is higher than 10 days ago. Exit, stop, size, kill
                       switch unchanged. Numbers (50, 10) are the ones used in
                       the analysis, fixed before this backtest.

Because the idea came from looking at train trades, train is NOT evidence for
it. It is judged on: the wide coin group (never used for this idea), the
fresh slice (prices after the test slice) and walk-forward.
"""

import pandas as pd
from pandas import DataFrame

from trend_ema import TrendEma

BTC_SMA = 50
BTC_SLOPE_DAYS = 10


def btc_daily_rising(daily: DataFrame, sma: int = BTC_SMA, days: int = BTC_SLOPE_DAYS) -> DataFrame:
    """Daily candles -> [available_from, btc_rising].

    A daily candle dated D (its open) is only complete at D + 1 day, so its
    value may be used from then on (no lookahead).
    """
    s = daily["close"].rolling(sma).mean()
    out = pd.DataFrame({
        "available_from": daily["date"] + pd.Timedelta(days=1),
        "btc_rising": (s > s.shift(days)).to_numpy(),
    })  # fmt: skip
    return out


def attach_btc_rising(
    hourly: DataFrame, daily: DataFrame, sma: int = BTC_SMA, days: int = BTC_SLOPE_DAYS
) -> pd.Series:
    """For each hourly candle: the latest btc_rising value that was already known."""
    flags = btc_daily_rising(daily, sma, days).sort_values("available_from")
    # Freqtrade's hourly and daily frames can use different time units (ms vs us);
    # merge_asof needs identical key types, so both go to nanoseconds.
    flags["available_from"] = flags["available_from"].astype("datetime64[ns, UTC]")
    left = hourly[["date"]].astype({"date": "datetime64[ns, UTC]"}).sort_values("date")
    merged = pd.merge_asof(
        left, flags,
        left_on="date", right_on="available_from", direction="backward",
    )  # fmt: skip
    return pd.Series(merged["btc_rising"].fillna(False).astype(bool).to_numpy(), index=hourly.index)


class TrendEmaBtcRising(TrendEma):
    """Only buy while Bitcoin's daily trend (SMA50) is going up."""

    btc_sma = BTC_SMA
    btc_days = BTC_SLOPE_DAYS

    def informative_pairs(self):
        return [("BTC/USDT", "1d")]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["btc_rising"] = True
        dp = getattr(self, "dp", None)  # missing in plain unit tests
        if dp is not None:
            daily = dp.get_pair_dataframe("BTC/USDT", "1d")
            if daily is not None and not daily.empty:
                dataframe["btc_rising"] = attach_btc_rising(dataframe, daily, self.btc_sma, self.btc_days)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if "enter_long" in dataframe:
            dataframe.loc[~dataframe["btc_rising"], ["enter_long", "enter_tag"]] = (0, None)
        return dataframe


# --- Sensitivity neighbours (NOT candidates): each moves ONE number --------------
# A real effect should survive small changes (a plateau); a lucky number collapses
# when moved (a spike, like EntryConfirm in round 7).


class BtcRisingSma40(TrendEmaBtcRising):
    btc_sma = 40


class BtcRisingSma60(TrendEmaBtcRising):
    btc_sma = 60


class BtcRisingDays5(TrendEmaBtcRising):
    btc_days = 5


class BtcRisingDays15(TrendEmaBtcRising):
    btc_days = 15


BTC_RISING_NEIGHBOURS = [BtcRisingSma40, BtcRisingSma60, BtcRisingDays5, BtcRisingDays15]


# --- Round 12: candidate + adding to winners -------------------------------------
# Train analysis of TrendEmaBtcRising (core, 381 trades): profit still comes only
# from the few long trends (3-14+ days: +5,172 USDT), while 253 trades held < 3 days
# lose -2,198, and only ~11% of the money is in coins. Round 8 showed that adding
# once to a winner (TrendEmaPyramid: +4%, same size, stop tightened so total risk
# stays 1%) is a plateau on train. One change vs TrendEmaBtcRising: that add.

from trend_variants import TrendEmaPyramid  # noqa: E402


class TrendEmaBtcRisingPyramid(TrendEmaBtcRising, TrendEmaPyramid):
    """BtcRising entries + TrendEmaPyramid's single add to winners (unchanged)."""


# --- Round 13: no entries hugging the trend line ------------------------------------
# Train analysis of TrendEmaBtcRising's entries (core, 381 trades), by how far the
# close was above EMA200 at the signal: bottom quartile (0.04-1.17% above) lost
# -123 USDT (win 25%); the next quartiles won +204, +1,523, +1,371. An entry right
# at the trend line is often a cross that fails straight back below it.
# Round number fixed BEFORE the backtest: at least 1% above EMA200.

MIN_GAP_ABOVE_TREND = 0.01


class TrendEmaBtcRisingGap(TrendEmaBtcRising):
    """BtcRising, but the close must be at least 1% above EMA200 to buy."""

    min_gap = MIN_GAP_ABOVE_TREND

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if "enter_long" in dataframe:
            hugging = dataframe["close"] < dataframe["ema_trend"] * (1 + self.min_gap)
            dataframe.loc[hugging, ["enter_long", "enter_tag"]] = (0, None)
        return dataframe


class BtcRisingGap05(TrendEmaBtcRisingGap):
    min_gap = 0.005


class BtcRisingGap2(TrendEmaBtcRisingGap):
    min_gap = 0.02


GAP_NEIGHBOURS = [BtcRisingGap05, BtcRisingGap2]


# --- Round 14: protect trades that were clearly winning ------------------------------
# Train analysis of TrendEmaBtcRisingGap (core, 310 trades), grouped by the best
# unrealized gain each trade reached (max_rate): trades that reached +2..10% and
# then fell back ended at about zero or worse (107 trades, -414 USDT), giving
# back 5-7 points. Classic fix: once a trade has been up enough, move the stop
# to break-even (entry + fees) so a good start can't turn into a loss.
# Round numbers fixed BEFORE the backtest: trigger +5%, stop at entry +0.5%
# (covers the 2 x 0.15% fee). Before the trigger the -8% stop is unchanged.

from datetime import datetime  # noqa: E402

from freqtrade.persistence import Trade  # noqa: E402
from freqtrade.strategy import stoploss_from_absolute  # noqa: E402

BREAKEVEN_TRIGGER = 0.05
BREAKEVEN_LOCK = 0.005


class TrendEmaGapBreakeven(TrendEmaBtcRisingGap):
    """Gap candidate + break-even stop once the trade has been +5% at its best."""

    use_custom_stoploss = True
    be_trigger = BREAKEVEN_TRIGGER
    be_lock = BREAKEVEN_LOCK

    def custom_stoploss(
        self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
        current_profit: float, after_fill: bool, **kwargs,
    ) -> float | None:  # fmt: skip
        best = (trade.max_rate or trade.open_rate) / trade.open_rate - 1
        if best < self.be_trigger:
            return None  # keep the normal -8% stop
        return stoploss_from_absolute(trade.open_rate * (1 + self.be_lock), current_rate)


class GapBreakeven3(TrendEmaGapBreakeven):
    be_trigger = 0.03


class GapBreakeven8(TrendEmaGapBreakeven):
    be_trigger = 0.08


BREAKEVEN_NEIGHBOURS = [GapBreakeven3, GapBreakeven8]


# --- Research only: does Gap keep its Calmar with more money in coins? -------------
# Pre-registered 2026-11-01 (docs/research/04). Same rule as TrendEmaBtcRisingGap,
# but 2% risk per trade instead of 1%. With the -8% stop that is 25% of capital per
# trade, exactly the live 25% cap, which stays. Like research_risk.TrendEmaRisk2 it
# refuses every entry outside backtest/hyperopt, so it can never trade, even by mistake.

from trend_ema import MAX_STAKE_RATIO, STOPLOSS, risk_based_stake  # noqa: E402

GAP_RESEARCH_RISK = 0.02


class TrendEmaBtcRisingGapRisk2(TrendEmaBtcRisingGap):
    """Gap with 2% risk per trade. BACKTEST ONLY."""

    def custom_stake_amount(
        self, pair: str, current_time: datetime, current_rate: float, proposed_stake: float,
        min_stake: float | None, max_stake: float, leverage: float, entry_tag: str | None,
        side: str, **kwargs,
    ) -> float:  # fmt: skip
        capital = self.wallets.get_total_stake_amount()
        stake = risk_based_stake(capital, GAP_RESEARCH_RISK, STOPLOSS, MAX_STAKE_RATIO)
        return min(stake, max_stake)

    def confirm_trade_entry(self, pair: str, *args, **kwargs) -> bool:
        runmode = getattr(getattr(getattr(self, "dp", None), "runmode", None), "value", None)
        if runmode not in ("backtest", "hyperopt"):
            return False  # research class: never trades with real or fake money
        return super().confirm_trade_entry(pair, *args, **kwargs)


# --- Same idea, slower candles (pre-registered 2026-11-01) --------------------------
# Like TrendEma4h vs TrendEma: everything identical, only 4-hour candles. EMA lengths
# and protection windows count candles, so they cover 4x more time.


class TrendEmaBtcRisingGap4h(TrendEmaBtcRisingGap):
    timeframe = "4h"
