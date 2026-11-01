"""Round 15: volatility targeting (position size from how wild the coin is).

Pre-registered 2026-11-01, before any backtest (docs/journal.md):
Professional trend followers size each position so every coin moves the account
by about the same amount: wild coin -> small position, calm coin -> big one
(docs/research/01, item 2). TrendEma gives every coin the same 12.5% stake.

    TrendEmaVolTarget  TrendEma entries and exits. Stake = 12.5% x min(1, 60% / the
                       coin's realized volatility), where realized volatility is the
                       annualized standard deviation of the last 30 days of hourly
                       returns. It can only SHRINK the live stake, never grow it, so
                       the 1% risk rule (R2) and the 25% cap (R4) still hold.

One fixed number: 60% annualized (round, roughly Bitcoin's usual level).
Success criterion, fixed in advance: Calmar above TrendEma on at least 3 of the
4 train coin groups AND at least 2 of the 3 validation groups.
"""

from datetime import datetime

import numpy as np
import pandas as pd
from pandas import DataFrame

from trend_ema import MAX_STAKE_RATIO, RISK_PER_TRADE, TrendEma, risk_based_stake

TARGET_VOL = 0.60  # annualized
VOL_WINDOW = 24 * 30  # 30 days of 1h candles
HOURS_PER_YEAR = 24 * 365


def realized_vol(close: pd.Series, window: int = VOL_WINDOW) -> pd.Series:
    """Annualized volatility of hourly log returns over the last `window` candles."""
    returns = np.log(close).diff()
    return returns.rolling(window).std() * np.sqrt(HOURS_PER_YEAR)


def vol_scale(vol: float, target: float = TARGET_VOL) -> float:
    """How much of the normal stake to use: 1 for calm coins, less for wild ones."""
    if not np.isfinite(vol) or vol <= 0:
        return 1.0  # no reading yet: behave like TrendEma
    return min(1.0, target / vol)


class TrendEmaVolTarget(TrendEma):
    """TrendEma with a smaller position on coins wilder than 60% a year."""

    startup_candle_count = 2 * 200 + VOL_WINDOW
    target_vol = TARGET_VOL

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["rvol"] = realized_vol(dataframe["close"])
        return dataframe

    def custom_stake_amount(
        self, pair: str, current_time: datetime, current_rate: float, proposed_stake: float,
        min_stake: float | None, max_stake: float, leverage: float, entry_tag: str | None,
        side: str, **kwargs,
    ) -> float:  # fmt: skip
        capital = self.wallets.get_total_stake_amount()
        stake = risk_based_stake(capital, RISK_PER_TRADE, self.stoploss, MAX_STAKE_RATIO)
        vol = float("nan")
        dp = getattr(self, "dp", None)
        if dp is not None:
            dataframe, _ = dp.get_analyzed_dataframe(pair, self.timeframe)
            if dataframe is not None and not dataframe.empty and "rvol" in dataframe:
                vol = float(dataframe["rvol"].iloc[-1])
        return min(stake * vol_scale(vol, self.target_vol), max_stake)


# Sensitivity neighbours (NOT candidates): only the target number moves.


class VolTarget45(TrendEmaVolTarget):
    target_vol = 0.45


class VolTarget80(TrendEmaVolTarget):
    target_vol = 0.80


VOL_NEIGHBOURS = [VolTarget45, VolTarget80]


# --- Pre-registered combination (2026-11-01): VolTarget sizing + BtcRising entry gate.
# No new numbers. Criterion fixed in docs/journal.md before the run.

from regime import TrendEmaBtcRising  # noqa: E402


class TrendEmaVolTargetBtc(TrendEmaBtcRising, TrendEmaVolTarget):
    """BtcRising entries (BTC daily SMA50 rising) + VolTarget stake (60%)."""


# --- Pre-registered 2026-11-01 (before any run): pick the coins by trading volume.
# Instead of 5 fixed coins, look at a big pool (every coin group we have) and only
# open new trades on the TOP_N coins with the highest USDT trading volume over the
# last 30 days, measured up to the PREVIOUS candle (no lookahead). Busy coins have
# tighter spreads and less slippage; the list changes as the market changes.
# Idea: Zarattini, Pagani & Barbon (2025), "Catching Crypto Trends" (volume-ranked
# universe). Numbers fixed now: top 15, 30 days. Everything else = TrendEmaVolTarget.

TOP_N = 15
VOLUME_WINDOW = 24 * 30


def volume_rank_flags(frames: dict[str, DataFrame], top_n: int = TOP_N, window: int = VOLUME_WINDOW) -> DataFrame:
    """date x pair table: True where the pair is among the top_n by 30-day USDT volume.

    Uses volumes up to the previous candle only (shift 1). A pair without a full
    window of history is not ranked (never in the top).
    """
    qv = {}
    for pair, df in frames.items():
        s = (df["close"] * df["volume"]).set_axis(pd.DatetimeIndex(df["date"]))
        qv[pair] = s.rolling(window, min_periods=window).sum().shift(1)
    table = pd.DataFrame(qv).sort_index()
    ranks = table.rank(axis=1, ascending=False, method="first")
    return ranks.le(top_n) & table.notna()


class TrendEmaVolTargetTopVol(TrendEmaVolTarget):
    """TrendEmaVolTarget, but new entries only on the 15 busiest coins of the pool."""

    top_n = TOP_N
    _flags_cache: dict = {}

    def _flags(self) -> DataFrame | None:
        dp = getattr(self, "dp", None)
        if dp is None:
            return None
        pairs = tuple(sorted(dp.current_whitelist()))
        frames = {}
        for p in pairs:
            df = dp.get_pair_dataframe(p, self.timeframe)
            if df is not None and not df.empty:
                frames[p] = df
        if not frames:
            return None
        key = (pairs, self.top_n, max(len(f) for f in frames.values()), max(f["date"].iloc[-1] for f in frames.values()))
        if key not in self._flags_cache:
            type(self)._flags_cache = {key: volume_rank_flags(frames, self.top_n)}  # keep only the latest
        return self._flags_cache[key]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["in_top"] = True  # unit tests without a data provider
        flags = self._flags()
        if flags is not None and metadata.get("pair") in flags:
            col = flags[metadata["pair"]]
            dates = pd.DatetimeIndex(dataframe["date"])
            dataframe["in_top"] = col.reindex(dates).fillna(False).astype(bool).to_numpy()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if "enter_long" in dataframe:
            dataframe.loc[~dataframe["in_top"], ["enter_long", "enter_tag"]] = (0, None)
        return dataframe
