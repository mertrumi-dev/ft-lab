"""TrendSmaDaily: hold a coin while its daily close is above its 200-day average.

Idea source (no code copied): Mebane Faber (2007), "A Quantitative Approach to
Tactical Asset Allocation" (Journal of Wealth Management), the classic
"price above the 10-month / 200-day moving average = invested, below = cash" rule.
It is the most cited simple trend rule; we use its textbook number (200 days),
not a tuned one.

Why now (2026-11-01): our hourly EMA rules lost their edge on the final test
(many failed hourly breakouts). Daily candles give far fewer, slower signals.

Our risk rules stay (inherited from TrendEma): the -8% hard stop, 1% risk per
trade (12.5% of capital per coin), max 3 open trades, protections, kill switch.
Entry:  daily close above SMA200.
Exit:   daily close below SMA200.
"""

from pandas import DataFrame

from trend_ema import TrendEma

SMA_DAYS = 200


class TrendSmaDaily(TrendEma):
    timeframe = "1d"
    startup_candle_count: int = SMA_DAYS + 10

    @property
    def protections(self):
        # TrendEma's protections count 1h candles; on daily candles keep them short.
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 1},
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 1,
                "trade_limit": 3,
                "stop_duration_candles": 1,
                "only_per_pair": False,
            },
        ]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["sma"] = dataframe["close"].rolling(SMA_DAYS).mean()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["close"] > dataframe["sma"]) & (dataframe["volume"] > 0),
            ["enter_long", "enter_tag"],
        ] = (1, "above_sma200d")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["close"] < dataframe["sma"]) & (dataframe["volume"] > 0),
            ["exit_long", "exit_tag"],
        ] = (1, "below_sma200d")
        return dataframe
