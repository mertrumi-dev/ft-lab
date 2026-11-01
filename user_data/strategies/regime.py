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
