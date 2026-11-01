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


def realized_vol(close: pd.Series, window: int = VOL_WINDOW, periods_per_year: int = HOURS_PER_YEAR) -> pd.Series:
    """Annualized volatility of per-candle log returns over the last `window` candles."""
    returns = np.log(close).diff()
    return returns.rolling(window).std() * np.sqrt(periods_per_year)


def vol_scale(vol: float, target: float = TARGET_VOL) -> float:
    """How much of the normal stake to use: 1 for calm coins, less for wild ones."""
    if not np.isfinite(vol) or vol <= 0:
        return 1.0  # no reading yet: behave like TrendEma
    return min(1.0, target / vol)


class TrendEmaVolTarget(TrendEma):
    """TrendEma with a smaller position on coins wilder than 60% a year."""

    startup_candle_count = 2 * 200 + VOL_WINDOW
    target_vol = TARGET_VOL
    vol_window = VOL_WINDOW  # candles in 30 days
    periods_per_year = HOURS_PER_YEAR  # candles in a year

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["rvol"] = realized_vol(dataframe["close"], self.vol_window, self.periods_per_year)
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


# --- Round 16 (pre-registered 2026-11-01): portfolio-level volatility budget --------
# Coins move together (when BTC falls, they all fall), so three open trades are
# closer to one big bet than to three small ones. Rule: the open trades'
# "volatility load" sum(stake / capital x coin volatility), counting the new trade,
# may not exceed 15% (round number). Correlation is assumed to be 1 (worst case).
# A new stake can only shrink because of it, so R2/R4 still hold.

from freqtrade.persistence import Trade  # noqa: E402

PORTFOLIO_VOL_BUDGET = 0.15


def portfolio_room(open_loads: list[float], budget: float = PORTFOLIO_VOL_BUDGET) -> float:
    """How much volatility load is still free for a new trade (never negative)."""
    return max(0.0, budget - sum(open_loads))


class TrendEmaVolTargetPortfolio(TrendEmaVolTarget):
    """VolTarget, plus a 15% cap on the summed volatility load of all open trades."""

    vol_budget = PORTFOLIO_VOL_BUDGET

    def _vol_now(self, pair: str) -> float:
        dp = getattr(self, "dp", None)
        if dp is None:
            return float("nan")
        dataframe, _ = dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or dataframe.empty or "rvol" not in dataframe:
            return float("nan")
        return float(dataframe["rvol"].iloc[-1])

    def custom_stake_amount(
        self, pair: str, current_time: datetime, current_rate: float, proposed_stake: float,
        min_stake: float | None, max_stake: float, leverage: float, entry_tag: str | None,
        side: str, **kwargs,
    ) -> float:  # fmt: skip
        stake = super().custom_stake_amount(
            pair, current_time, current_rate, proposed_stake, min_stake, max_stake, leverage, entry_tag, side, **kwargs
        )
        vol = self._vol_now(pair)
        if not np.isfinite(vol) or vol <= 0:
            return stake  # no reading: behave like VolTarget
        capital = self.wallets.get_total_stake_amount()
        loads = []
        for t in Trade.get_trades_proxy(is_open=True):
            v = self._vol_now(t.pair)
            loads.append(t.stake_amount / capital * (v if np.isfinite(v) else vol))
        room = portfolio_room(loads, self.vol_budget)
        return min(stake, capital * room / vol)


# --- Coin selection v2 (pre-registered 2026-11-01) ----------------------------------
# Core 5 always allowed. Other pool coins only while BOTH hold: among the top 20 by
# 30-day USDT volume (up to the previous candle) AND the coin's own daily close is
# above its 200-day SMA (completed days only, used from the next midnight).

CORE_PAIRS = ("BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT")
POOL2_TOP_N = 20
DAILY_SMA = 200


def daily_above_sma(daily: DataFrame, hourly_dates: pd.Series, length: int = DAILY_SMA) -> np.ndarray:
    """For each hourly time: was the last COMPLETED daily close above its daily SMA?"""
    sma = daily["close"].rolling(length).mean()
    flags = pd.DataFrame({
        "available_from": (daily["date"] + pd.Timedelta(days=1)).astype("datetime64[ns, UTC]"),
        "above": (daily["close"] > sma).to_numpy(),
    }).sort_values("available_from")  # fmt: skip
    left = pd.DataFrame({"date": pd.DatetimeIndex(hourly_dates).astype("datetime64[ns, UTC]")})
    merged = pd.merge_asof(left, flags, left_on="date", right_on="available_from", direction="backward")
    return merged["above"].fillna(False).astype(bool).to_numpy()


class TrendEmaVolTargetPool2(TrendEmaVolTargetTopVol):
    """Core 5 always; other coins only if top-20 by volume AND above their daily SMA200."""

    top_n = POOL2_TOP_N

    def informative_pairs(self):
        dp = getattr(self, "dp", None)
        pairs = dp.current_whitelist() if dp is not None else []
        return [(p, "1d") for p in pairs]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)  # sets in_top (top 20)
        pair = metadata.get("pair")
        if pair in CORE_PAIRS:
            dataframe["in_top"] = True
            return dataframe
        dp = getattr(self, "dp", None)
        if dp is not None:
            daily = dp.get_pair_dataframe(pair, "1d")
            above = daily_above_sma(daily, dataframe["date"]) if daily is not None and not daily.empty else False
            dataframe["in_top"] = dataframe["in_top"] & above
        return dataframe


# --- Pullback entry (pre-registered 2026-11-01) --------------------------------------
# The VolTarget entry signal only ARMS the trade. It is bought on the first candle in the
# next 12 where the low touches EMA20 while the trend is intact (EMA20 > EMA50 and
# close > EMA200). No touch within 12 candles = the signal is skipped. Number fixed: 12.

PULLBACK_WINDOW = 12


def pullback_entries(dataframe: DataFrame, window: int = PULLBACK_WINDOW) -> pd.Series:
    """True on the first candle after an armed cross where price touches EMA20 (no lookahead)."""
    armed_at = pd.Series(np.where(
        (dataframe["ema_fast"] > dataframe["ema_slow"])
        & (dataframe["ema_fast"].shift(1) <= dataframe["ema_slow"].shift(1))
        & (dataframe["close"] > dataframe["ema_trend"]),
        np.arange(len(dataframe)), np.nan), index=dataframe.index)  # fmt: skip
    last_arm = armed_at.ffill()
    age = np.arange(len(dataframe)) - last_arm  # candles since the last arming
    touch = (
        (age >= 1) & (age <= window)
        & (dataframe["low"] <= dataframe["ema_fast"])
        & (dataframe["ema_fast"] > dataframe["ema_slow"])
        & (dataframe["close"] > dataframe["ema_trend"])
        & (dataframe["volume"] > 0)
    )  # fmt: skip
    first = touch & ~touch.groupby(last_arm).cumsum().gt(1)
    return first.fillna(False).astype(bool)


class TrendEmaVolTargetPullback(TrendEmaVolTarget):
    """VolTarget, but buy the first dip to EMA20 within 12 candles after the signal."""

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[pullback_entries(dataframe), ["enter_long", "enter_tag"]] = (1, "pullback_ema20")
        return dataframe


# --- Same rule on 2-hour candles (pre-registered 2026-11-01) --------------------------
# Fewer trades = less fee (the one lever that helped consistently). EMA lengths and
# protections count candles (2x the time, like TrendEma4h). Volatility still covers 30
# days and is annualized for 2h candles, so the 60% target means the same thing.


class TrendEmaVolTarget2h(TrendEmaVolTarget):
    timeframe = "2h"
    vol_window = 12 * 30
    periods_per_year = 12 * 365
    startup_candle_count = 2 * 200 + 12 * 30
