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

import json
from datetime import datetime, timedelta
from pathlib import Path

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


# --- Equity-curve de-risking (pre-registered 2026-11-01) ----------------------------
# When the account's realized equity (closed trades, the same measure as the kill
# switch) is more than 10% below its peak, stakes are halved; they stay halved until
# equity is back within 5% of the peak. Computed from the trade history every time,
# so a restart cannot reset it. Only shrinks the stake: R2/R4 and the 20% kill switch stay.

DERISK_START = 0.10
DERISK_END = 0.05
DERISK_FACTOR = 0.5


def derisk_active(starting: float, closed_profits: list[float],
                  start: float = DERISK_START, end: float = DERISK_END) -> bool:  # fmt: skip
    """Walk the closed trades in order and return whether de-risking is on now."""
    equity = peak = starting
    on = False
    for profit in closed_profits:
        equity += profit
        peak = max(peak, equity)
        dd = (peak - equity) / peak if peak > 0 else 0.0
        if not on and dd > start:
            on = True
        elif on and dd <= end:
            on = False
    return on


class TrendEmaVolTargetDerisk(TrendEmaVolTarget):
    """VolTarget, with half-size trades while realized equity is >10% below its peak."""

    def custom_stake_amount(
        self, pair: str, current_time: datetime, current_rate: float, proposed_stake: float,
        min_stake: float | None, max_stake: float, leverage: float, entry_tag: str | None,
        side: str, **kwargs,
    ) -> float:  # fmt: skip
        stake = super().custom_stake_amount(
            pair, current_time, current_rate, proposed_stake, min_stake, max_stake, leverage, entry_tag, side, **kwargs
        )
        closed = sorted(Trade.get_trades_proxy(is_open=False), key=lambda t: t.close_date_utc)
        if derisk_active(self.wallets.get_starting_balance(), [t.close_profit_abs or 0.0 for t in closed]):
            return stake * DERISK_FACTOR
        return stake


# --- Volatility stop (pre-registered 2026-11-01) --------------------------------------
# Stop = entry - 3 x ATR(14) of the signal candle, never wider than -8% and never tighter
# than -3%. Stake = 1% of equity / stop distance (cap 25%) x the VolTarget scale, so a
# stop-out still costs at most 1% (R2) and R4 holds.

from freqtrade.strategy import stoploss_from_absolute  # noqa: E402
from trend_variants import atr  # noqa: E402

ATR_STOP_MULT = 3.0
STOP_MIN, STOP_MAX = 0.03, 0.08


def atr_stop_distance(close: float, atr_value: float, mult: float = ATR_STOP_MULT) -> float:
    """Stop distance as a ratio of price, clipped to [3%, 8%]; 8% if ATR is unknown."""
    if not np.isfinite(atr_value) or atr_value <= 0 or close <= 0:
        return STOP_MAX
    return float(min(STOP_MAX, max(STOP_MIN, mult * atr_value / close)))


class TrendEmaVolTargetAtrStop(TrendEmaVolTarget):
    """VolTarget with a 3xATR stop (3%..8%) and the 1%-risk stake sized to that stop."""

    use_custom_stoploss = True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["atr"] = atr(dataframe)
        return dataframe

    def _signal_row(self, pair: str, when=None):
        dp = getattr(self, "dp", None)
        if dp is None:
            return None
        df, _ = dp.get_analyzed_dataframe(pair, self.timeframe)
        if df is None or df.empty:
            return None
        if when is None:
            return df.iloc[-1]
        rows = df[df["date"] < when]  # the candle that produced the entry signal
        return rows.iloc[-1] if not rows.empty else None

    def custom_stake_amount(
        self, pair: str, current_time: datetime, current_rate: float, proposed_stake: float,
        min_stake: float | None, max_stake: float, leverage: float, entry_tag: str | None,
        side: str, **kwargs,
    ) -> float:  # fmt: skip
        row = self._signal_row(pair)
        dist = atr_stop_distance(float(row["close"]), float(row["atr"])) if row is not None else STOP_MAX
        vol = float(row["rvol"]) if row is not None and "rvol" in row else float("nan")
        capital = self.wallets.get_total_stake_amount()
        stake = risk_based_stake(capital, RISK_PER_TRADE, -dist, MAX_STAKE_RATIO)
        return min(stake * vol_scale(vol, self.target_vol), max_stake)

    def custom_stoploss(
        self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
        current_profit: float, after_fill: bool, **kwargs,
    ) -> float | None:  # fmt: skip
        row = self._signal_row(pair, trade.open_date_utc)
        if row is None:
            return None  # keep the -8% hard stop
        dist = atr_stop_distance(float(row["close"]), float(row["atr"]))
        return stoploss_from_absolute(trade.open_rate * (1 - dist), current_rate)


# --- Breadth gate (pre-registered 2026-11-01) -----------------------------------------
# New entries only while at least 3 of the "breadth set" close above their 1h EMA200
# (simple majority, not tuned). Breadth set = the first 5 pairs of the bot's list that
# have data (core: the bot's 5 coins). Exits unchanged. Same-candle values only.

BREADTH_SET_SIZE = 5
BREADTH_MIN_UP = 3


def breadth_count(frames: dict[str, DataFrame], trend_len: int = 200) -> pd.Series:
    """date -> how many of the given pairs closed above their EMA(trend_len) on that candle."""
    ups = {}
    for pair, df in frames.items():
        c = df["close"].set_axis(pd.DatetimeIndex(df["date"]))
        ups[pair] = (c > c.ewm(span=trend_len, adjust=False).mean()).astype(int)
    return pd.DataFrame(ups).sort_index().fillna(0).sum(axis=1)


class TrendEmaVolTargetBreadth(TrendEmaVolTarget):
    """VolTarget, new trades only while >= 3 of the 5 breadth coins are above their EMA200."""

    _breadth_cache: dict = {}

    def _breadth(self) -> pd.Series | None:
        dp = getattr(self, "dp", None)
        if dp is None:
            return None
        frames = {}
        for p in dp.current_whitelist():
            df = dp.get_pair_dataframe(p, self.timeframe)
            if df is not None and not df.empty:
                frames[p] = df
            if len(frames) == BREADTH_SET_SIZE:
                break
        if not frames:
            return None
        key = (tuple(frames), max(len(f) for f in frames.values()), max(f["date"].iloc[-1] for f in frames.values()))
        if key not in self._breadth_cache:
            type(self)._breadth_cache = {key: breadth_count(frames)}
        return self._breadth_cache[key]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["breadth_ok"] = True  # unit tests without a data provider
        b = self._breadth()
        if b is not None:
            dataframe["breadth_ok"] = (b.reindex(pd.DatetimeIndex(dataframe["date"])).fillna(0) >= BREADTH_MIN_UP).to_numpy()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if "enter_long" in dataframe:
            dataframe.loc[~dataframe["breadth_ok"], ["enter_long", "enter_tag"]] = (0, None)
        return dataframe


# --- VolTarget plateau check (train only, research; NOT candidates, never in the bot) --
# Each neighbour moves ONE number. -10% stop is outside R1 on purpose: it only measures
# how sensitive the result is to the stop; the live rule stays -8%.


class _VolTargetLens(TrendEmaVolTarget):
    fast_len, slow_len, trend_len = 20, 50, 200

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        from trend_ema import ema

        dataframe["ema_fast"] = ema(dataframe["close"], self.fast_len)
        dataframe["ema_slow"] = ema(dataframe["close"], self.slow_len)
        dataframe["ema_trend"] = ema(dataframe["close"], self.trend_len)
        dataframe["rvol"] = realized_vol(dataframe["close"], self.vol_window, self.periods_per_year)
        return dataframe


class VTFast15(_VolTargetLens):
    fast_len = 15


class VTFast25(_VolTargetLens):
    fast_len = 25


class VTSlow40(_VolTargetLens):
    slow_len = 40


class VTSlow60(_VolTargetLens):
    slow_len = 60


class VTTrend150(_VolTargetLens):
    trend_len = 150


class VTTrend250(_VolTargetLens):
    trend_len = 250
    startup_candle_count = 2 * 250 + VOL_WINDOW


class VTStop6(TrendEmaVolTarget):
    stoploss = -0.06


class VTStop10(TrendEmaVolTarget):
    stoploss = -0.10


class VTVol480(TrendEmaVolTarget):
    vol_window = 480


class VTVol960(TrendEmaVolTarget):
    vol_window = 960
    startup_candle_count = 2 * 200 + 960


VT_NEIGHBOURS = [VTFast15, VTFast25, VTSlow40, VTSlow60, VTTrend150, VTTrend250, VTStop6, VTStop10, VTVol480, VTVol960]


# --- Regime-dependent target vol (pre-registered 2026-11-01, research 06 backlog) ------
# Same label as scripts/regimes.py: BTC bull = last CLOSED daily close above SMA200 AND
# SMA200 higher than 20 days earlier. In a bull regime the target is 80%, else 60%.
# min(1, target / vol) still caps the stake at the base 12.5%, so R2/R4 hold.

BULL_SMA, BULL_SLOPE_DAYS = 200, 20
BULL_TARGET_VOL = 0.80


def btc_bull_flags(daily: DataFrame, hourly_dates: pd.Series, sma: int = BULL_SMA, days: int = BULL_SLOPE_DAYS) -> np.ndarray:
    """For each hourly time: was BTC in a bull regime at the last COMPLETED daily close?"""
    s = daily["close"].rolling(sma).mean()
    bull = (daily["close"] > s) & (s > s.shift(days))
    flags = pd.DataFrame({
        "available_from": (daily["date"] + pd.Timedelta(days=1)).astype("datetime64[ns, UTC]"),
        "bull": bull.to_numpy(),
    }).sort_values("available_from")  # fmt: skip
    left = pd.DataFrame({"date": pd.DatetimeIndex(hourly_dates).astype("datetime64[ns, UTC]")})
    merged = pd.merge_asof(left, flags, left_on="date", right_on="available_from", direction="backward")
    return merged["bull"].fillna(False).astype(bool).to_numpy()


class TrendEmaVolTargetBullVol(TrendEmaVolTarget):
    """VolTarget with an 80% target while BTC is in a bull regime, 60% otherwise."""

    bull_target_vol = BULL_TARGET_VOL

    def informative_pairs(self):
        return [("BTC/USDT", "1d")]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["btc_bull"] = False
        dp = getattr(self, "dp", None)
        if dp is not None:
            daily = dp.get_pair_dataframe("BTC/USDT", "1d")
            if daily is not None and not daily.empty:
                dataframe["btc_bull"] = btc_bull_flags(daily, dataframe["date"])
        return dataframe

    def custom_stake_amount(
        self, pair: str, current_time: datetime, current_rate: float, proposed_stake: float,
        min_stake: float | None, max_stake: float, leverage: float, entry_tag: str | None,
        side: str, **kwargs,
    ) -> float:  # fmt: skip
        capital = self.wallets.get_total_stake_amount()
        stake = risk_based_stake(capital, RISK_PER_TRADE, self.stoploss, MAX_STAKE_RATIO)
        vol, bull = float("nan"), False
        dp = getattr(self, "dp", None)
        if dp is not None:
            dataframe, _ = dp.get_analyzed_dataframe(pair, self.timeframe)
            if dataframe is not None and not dataframe.empty and "rvol" in dataframe:
                vol = float(dataframe["rvol"].iloc[-1])
                bull = bool(dataframe["btc_bull"].iloc[-1]) if "btc_bull" in dataframe else False
        target = self.bull_target_vol if bull else self.target_vol
        return min(stake * vol_scale(vol, target), max_stake)


# --- KAMA instead of the fast EMA (pre-registered 2026-11-01, research 06: sideways whipsaws) ---
# Kaufman's Adaptive Moving Average, textbook numbers (10, 2, 30), Smarter Trading (1995).
# Efficiency ratio ER = |net move over 10 candles| / sum of the 10 single-candle moves:
# 1 = a straight line (trend), near 0 = back and forth (chop). The smoothing constant
# goes from the 30-period EMA speed (chop) to the 2-period EMA speed (clean trend),
# squared so it slows down strongly in chop. Same output as TA-Lib's KAMA (tested).

KAMA_N, KAMA_FAST, KAMA_SLOW = 10, 2, 30


def kama(close: pd.Series, n: int = KAMA_N, fast: int = KAMA_FAST, slow: int = KAMA_SLOW) -> pd.Series:
    """Kaufman Adaptive Moving Average. NaN for the first n-1 candles, seeded with close[n-1]."""
    c = close.to_numpy(dtype=float)
    out = np.full(len(c), np.nan)
    if len(c) < n:
        return pd.Series(out, index=close.index)
    change = np.abs(c[n:] - c[:-n])  # net move over n candles, for i = n..len-1
    step = np.abs(np.diff(c))
    volatility = pd.Series(step).rolling(n).sum().to_numpy()[n - 1:]  # sum of the last n single moves
    er = np.divide(change, volatility, out=np.zeros_like(change), where=volatility > 0)
    fast_sc, slow_sc = 2 / (fast + 1), 2 / (slow + 1)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2
    out[n - 1] = c[n - 1]
    for i in range(n, len(c)):  # recursive: each value builds on the previous one
        out[i] = out[i - 1] + sc[i - n] * (c[i] - out[i - 1])
    return pd.Series(out, index=close.index)


class TrendEmaVolTargetKama(TrendEmaVolTarget):
    """VolTarget with KAMA(10, 2, 30) in place of EMA20: entry/exit = KAMA crossing EMA50."""

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["ema_fast"] = kama(dataframe["close"])  # TrendEma's entry/exit read this column
        return dataframe


# --- Daily trend rule (pre-registered 2026-11-01, research 10 backlog) -------------------
# The hourly EMA cross bled through whipsaw and fees in the final test (research 10). This is
# the same idea on DAILY candles, textbook numbers, no tuning:
#   entry: (EMA20 > EMA50 AND close > EMA50) turns from false to true
#   exit:  EMA20 crosses below EMA50, or the -8% stop (R1)
#   size:  VolTarget, 60% target, 30 daily returns annualized with sqrt(365)


class TrendEmaVolTargetDaily(TrendEmaVolTarget):
    """Daily-candle trend rule with VolTarget sizing (fewer trades, lower fees)."""

    timeframe = "1d"
    vol_window = 30  # daily candles in 30 days
    periods_per_year = 365
    startup_candle_count = 2 * 50 + 30

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        from trend_ema import ema

        dataframe["ema_fast"] = ema(dataframe["close"], 20)
        dataframe["ema_slow"] = ema(dataframe["close"], 50)
        dataframe["rvol"] = realized_vol(dataframe["close"], self.vol_window, self.periods_per_year)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        ok = (dataframe["ema_fast"] > dataframe["ema_slow"]) & (dataframe["close"] > dataframe["ema_slow"])
        dataframe.loc[ok & ~ok.shift(1, fill_value=False) & (dataframe["volume"] > 0), ["enter_long", "enter_tag"]] = (
            1, "daily_trend_up")  # fmt: skip
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        from trend_ema import crossed_below

        dataframe.loc[crossed_below(dataframe["ema_fast"], dataframe["ema_slow"]) & (dataframe["volume"] > 0),
                      ["exit_long", "exit_tag"]] = (1, "ema_cross_down")  # fmt: skip
        return dataframe


# --- Fee-aware entry filter (pre-registered 2026-11-01, research 10 lesson 1) -------------
# Fees were a quarter of the final-test loss. Enter only if the coin's typical hourly move
# (ATR(14) / close) covers the round-trip cost at least 3 times: 3 x 0.30% = 0.9%.
# The number comes from the cost (0.15% per side, the backtest fee), it was not tuned.

ROUND_TRIP_COST = 2 * 0.0015
FEE_COVER = 3


class TrendEmaVolTargetFeeAware(TrendEmaVolTarget):
    """VolTarget that skips entries when the expected hourly move is too small for the fees."""

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        from trend_variants import atr

        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["atr_pct"] = atr(dataframe) / dataframe["close"]
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if "enter_long" in dataframe:
            too_small = dataframe["atr_pct"] < FEE_COVER * ROUND_TRIP_COST
            dataframe.loc[too_small, ["enter_long", "enter_tag"]] = (0, None)
        return dataframe


# --- Longer cooldown after a signal exit (pre-registered 2026-11-01) ----------------------
# Fees are mostly a question of HOW MANY trades (research 10, FeeAware trial). After an
# ema_cross_down exit the same pair waits 24 candles (one day) before a new entry; stop exits
# keep the 2-candle CooldownPeriod. The strategy locks the pair itself (lock_pair), so the
# live/dry-run bot and the backtest apply exactly the same rule.

SIGNAL_EXIT_COOLDOWN_CANDLES = 24


class TrendEmaVolTargetCooldown24(TrendEmaVolTarget):
    """VolTarget that waits one day before re-entering a pair it just left on a signal."""

    signal_exit_cooldown = SIGNAL_EXIT_COOLDOWN_CANDLES

    def confirm_trade_exit(
        self, pair: str, trade, order_type: str, amount: float, rate: float, time_in_force: str,
        exit_reason: str, current_time: datetime, **kwargs,
    ) -> bool:  # fmt: skip
        if exit_reason == "ema_cross_down":
            from datetime import timedelta

            from freqtrade.exchange import timeframe_to_minutes

            until = current_time + timedelta(minutes=timeframe_to_minutes(self.timeframe) * self.signal_exit_cooldown)
            self.lock_pair(pair, until, reason=f"{self.signal_exit_cooldown} candles after a signal exit")
        return True


# Cooldown24 plateau neighbours (NOT candidates): only the cooldown length moves.
class VTCooldown12(TrendEmaVolTargetCooldown24):
    signal_exit_cooldown = 12


class VTCooldown48(TrendEmaVolTargetCooldown24):
    signal_exit_cooldown = 48


# --- Re-size an open trade when volatility doubles (pre-registered 2026-11-01) ------------
# VolTarget sizes a trade only at entry. If the coin's volatility rises so much that the
# size it would call for now is under HALF the size at entry, sell half of the position,
# once per trade. Only ever reduces; R2/R4 hold. "Half" is a natural unit, not tuned.


class TrendEmaVolTargetDerisk2x(TrendEmaVolTarget):
    """VolTarget that halves an open trade once if its volatility scale halves after entry."""

    position_adjustment_enable = True
    max_entry_position_adjustment = 0  # never adds to a trade

    def _scale_at(self, dataframe: DataFrame, when) -> float:
        """VolTarget scale from the last candle CLOSED before `when` (no lookahead)."""
        rows = dataframe[dataframe["date"] < pd.Timestamp(when) - pd.Timedelta(hours=1) + pd.Timedelta(seconds=1)]
        if rows.empty or "rvol" not in rows:
            return float("nan")
        return vol_scale(float(rows["rvol"].iloc[-1]), self.target_vol)

    def adjust_trade_position(self, trade, current_time, current_rate, current_profit, min_stake, max_stake,
                              current_entry_rate, current_exit_rate, current_entry_profit, current_exit_profit,
                              **kwargs):  # fmt: skip
        if trade.nr_of_successful_exits > 0 or getattr(trade, "has_open_orders", False):
            return None
        dp = getattr(self, "dp", None)
        if dp is None:
            return None
        dataframe, _ = dp.get_analyzed_dataframe(trade.pair, self.timeframe)
        if dataframe is None or dataframe.empty:
            return None
        at_entry = self._scale_at(dataframe, trade.open_date_utc)
        now = vol_scale(float(dataframe["rvol"].iloc[-1]), self.target_vol)
        if np.isfinite(at_entry) and now < 0.5 * at_entry:
            return -(trade.stake_amount / 2), "derisk_vol_2x"
        return None


SHORT_VOL_WINDOW = 72  # hours = 3 days (pre-registered 2026-11-01, not tuned)


class TrendEmaVolTargetDerisk72h(TrendEmaVolTargetDerisk2x):
    """Derisk2x with the CURRENT scale from a 72-hour volatility (entry scale stays 30-day)."""

    short_vol_window = SHORT_VOL_WINDOW

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["rvol_short"] = realized_vol(dataframe["close"], self.short_vol_window, self.periods_per_year)
        return dataframe

    def adjust_trade_position(self, trade, current_time, current_rate, current_profit, min_stake, max_stake,
                              current_entry_rate, current_exit_rate, current_entry_profit, current_exit_profit,
                              **kwargs):  # fmt: skip
        if trade.nr_of_successful_exits > 0 or getattr(trade, "has_open_orders", False):
            return None
        dp = getattr(self, "dp", None)
        if dp is None:
            return None
        dataframe, _ = dp.get_analyzed_dataframe(trade.pair, self.timeframe)
        if dataframe is None or dataframe.empty or "rvol_short" not in dataframe:
            return None
        at_entry = self._scale_at(dataframe, trade.open_date_utc)
        now = vol_scale(float(dataframe["rvol_short"].iloc[-1]), self.target_vol)
        if np.isfinite(at_entry) and now < 0.5 * at_entry:
            return -(trade.stake_amount / 2), "derisk_vol_72h"
        return None


# Derisk72h plateau neighbours (NOT candidates): only the short window moves.
class VTDerisk48h(TrendEmaVolTargetDerisk72h):
    short_vol_window = 48


class VTDerisk96h(TrendEmaVolTargetDerisk72h):
    short_vol_window = 96


# --- Minimum hold time (pre-registered 2026-11-01, "fee budget" family) -------------------
# Fees were 66% of VolTarget's alt2024b loss; trades shorter than 3 days lost money as a group
# (early trade breakdown). A signal exit is refused while the trade is younger than 24
# candles (one day); after that, the trade exits as soon as EMA20 is below EMA50. The -8%
# stop is never delayed (R1).

MIN_HOLD_CANDLES = 24


class TrendEmaVolTargetMinHold24(TrendEmaVolTarget):
    """VolTarget whose signal exit waits until the trade is at least one day old."""

    min_hold_candles = MIN_HOLD_CANDLES

    def _old_enough(self, trade, current_time) -> bool:
        from datetime import timedelta

        from freqtrade.exchange import timeframe_to_minutes

        return current_time - trade.open_date_utc >= timedelta(minutes=timeframe_to_minutes(self.timeframe) * self.min_hold_candles)

    def confirm_trade_exit(
        self, pair: str, trade, order_type: str, amount: float, rate: float, time_in_force: str,
        exit_reason: str, current_time: datetime, **kwargs,
    ) -> bool:  # fmt: skip
        if exit_reason == "ema_cross_down" and not self._old_enough(trade, current_time):
            return False  # too young: keep it (the stop still protects it)
        return True

    def custom_exit(self, pair: str, trade, current_time: datetime, current_rate: float, current_profit: float, **kwargs):
        if not self._old_enough(trade, current_time):
            return None
        dp = getattr(self, "dp", None)
        if dp is None:
            return None
        dataframe, _ = dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or dataframe.empty:
            return None
        last = dataframe.iloc[-1]
        if last["ema_fast"] < last["ema_slow"]:
            return "ema_below_after_minhold"
        return None


# --- Cross-sectional momentum gate (pre-registered 2026-11-01, inspired by the rotation bot) ---
# Enter only coins whose 30-day return (720 hourly closes, up to the previous candle) is in the
# top half of the group (rank <= ceil(n/2) among coins with data) AND above zero (absolute
# momentum, Antonacci). 30 days from the rotation rule, "half" a natural split; not tuned.

MOM_WINDOW = 24 * 30


def momentum_half_flags(frames: dict[str, DataFrame], window: int = MOM_WINDOW) -> DataFrame:
    """date x pair: True where the pair's past-window return is positive and in the top half."""
    ret = {}
    for pair, df in frames.items():
        c = df["close"].set_axis(pd.DatetimeIndex(df["date"]))
        ret[pair] = (c / c.shift(window) - 1).shift(1)  # known at the previous candle's close
    table = pd.DataFrame(ret).sort_index()
    n = table.notna().sum(axis=1)
    ranks = table.rank(axis=1, ascending=False, method="first")
    return ranks.le(np.ceil(n / 2), axis=0) & (table > 0)


class TrendEmaVolTargetMomHalf(TrendEmaVolTargetTopVol):
    """VolTarget entering only coins in the stronger half of the group (and rising over 30 days)."""

    _flags_cache: dict = {}

    def _flags(self) -> DataFrame | None:
        dp = getattr(self, "dp", None)
        if dp is None:
            return None
        pairs = tuple(sorted(dp.current_whitelist()))
        frames = {p: df for p in pairs if (df := dp.get_pair_dataframe(p, self.timeframe)) is not None and not df.empty}
        if not frames:
            return None
        key = (pairs, max(len(f) for f in frames.values()), max(f["date"].iloc[-1] for f in frames.values()))
        if key not in self._flags_cache:
            type(self)._flags_cache = {key: momentum_half_flags(frames)}
        return self._flags_cache[key]


# --- Trend-strength gate (pre-registered 2026-11-01, T108) ---------------------------------
# The final-test post-mortem: whipsaw/chop kills the hourly rule. Enter only when ADX(14) on the
# signal candle is above 20 (textbook "a real trend"). Same ADX as trend_variants.TrendEmaAdx,
# which FAILED on TrendEma on 2026-10-31; this re-tests it on VolTarget and new data.

ADX_GATE = 20


class TrendEmaVolTargetAdx(TrendEmaVolTarget):
    """VolTarget that only enters when ADX(14) says the market is trending."""

    adx_min = ADX_GATE

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        from trend_variants import adx

        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["adx"] = adx(dataframe)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if "enter_long" in dataframe:
            dataframe.loc[~(dataframe["adx"] > self.adx_min), ["enter_long", "enter_tag"]] = (0, None)
        return dataframe


# T108 plateau neighbours (NOT candidates, only run if T108 passes): only the threshold moves.
class VTAdx15(TrendEmaVolTargetAdx):
    adx_min = 15


class VTAdx25(TrendEmaVolTargetAdx):
    adx_min = 25


# --- Partial take-profit at 2R (pre-registered 2026-11-01, T109) ---------------------------
# When an open trade is up 2R (2 x the 8% stop distance = +16%), sell half of it once; the
# other half keeps the normal exits (EMA cross-down, -8% stop). "2R" is the textbook risk
# multiple, not tuned. Trade-off measured by the trial: profit locked on reversals vs the
# big trends (where most of the profit comes from) cut in half.

TAKE_PROFIT_R = 2


class TrendEmaVolTargetTakeHalf2R(TrendEmaVolTarget):
    """VolTarget that banks half of a trade once it is up 2R (+16%)."""

    position_adjustment_enable = True
    max_entry_position_adjustment = 0  # never adds

    def adjust_trade_position(self, trade, current_time, current_rate, current_profit, min_stake, max_stake,
                              current_entry_rate, current_exit_rate, current_entry_profit, current_exit_profit,
                              **kwargs):  # fmt: skip
        if trade.nr_of_successful_exits > 0 or getattr(trade, "has_open_orders", False):
            return None
        if current_profit >= TAKE_PROFIT_R * abs(self.stoploss):
            return -(trade.stake_amount / 2), "take_half_2r"
        return None


# --- Measured correlation gate (pre-registered 2026-11-01, T110) ----------------------------
# Three open trades on coins that move together are one big bet, not three small ones. The
# Portfolio trial only ASSUMED correlation 1; this measures it: a new entry is refused if its
# coin's 30-day hourly log-return correlation with ANY coin we already hold is >= 0.8
# (the usual "high correlation" mark; not tuned). The parent checks (kill switch, stale data)
# run first and are never skipped.

import logging  # noqa: E402

CORR_WINDOW = 24 * 30
CORR_MAX = 0.8
_corr_log = logging.getLogger(__name__)


def return_correlation(a: DataFrame, b: DataFrame, window: int = CORR_WINDOW) -> float:
    """Correlation of the last `window` hourly log returns of two analyzed dataframes (aligned on date)."""
    ra = np.log(a.set_index("date")["close"]).diff()
    rb = np.log(b.set_index("date")["close"]).diff()
    both = pd.concat([ra, rb], axis=1, join="inner").dropna().tail(window)
    if len(both) < window // 2:
        return float("nan")  # not enough shared history: no verdict
    return float(both.iloc[:, 0].corr(both.iloc[:, 1]))


class TrendEmaVolTargetLowCorr(TrendEmaVolTarget):
    """VolTarget that skips a new coin that moves too much like one already held."""

    corr_max = CORR_MAX

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float, time_in_force: str,
                            current_time: datetime, entry_tag: str | None, side: str, **kwargs) -> bool:  # fmt: skip
        if not super().confirm_trade_entry(pair, order_type, amount, rate, time_in_force, current_time, entry_tag, side, **kwargs):
            return False  # kill switch / stale data: never skipped
        dp = getattr(self, "dp", None)
        if dp is None:
            return True
        new, _ = dp.get_analyzed_dataframe(pair, self.timeframe)  # trimmed to now in backtests: no lookahead
        for trade in Trade.get_trades_proxy(is_open=True):
            if trade.pair == pair:
                continue
            held, _ = dp.get_analyzed_dataframe(trade.pair, self.timeframe)
            c = return_correlation(new, held)
            if np.isfinite(c) and c >= self.corr_max:
                _corr_log.warning("LOWCORR: %s refused, correlation %.2f with open %s", pair, c, trade.pair)
                return False
        return True


# T113. R9 ("losing-streak brake") is Freqtrade's StoplossGuard, which counts STOP exits only;
# the final-test post-mortem found 174 of 176 exits were signal exits, so in chop the brake
# hardly ever fires. Same numbers as R9 (3 trades in 24 candles -> 12 candles no new entries,
# all coins), but every trade closed at a loss counts, whatever the exit reason.
LOSS_GUARD_LOOKBACK = timedelta(hours=24)
LOSS_GUARD_LIMIT = 3
LOSS_GUARD_PAUSE = timedelta(hours=12)
_guard_log = logging.getLogger(__name__)


def loss_guard_until(loss_times: list[datetime], lookback: timedelta = LOSS_GUARD_LOOKBACK,
                     limit: int = LOSS_GUARD_LIMIT, pause: timedelta = LOSS_GUARD_PAUSE) -> datetime | None:  # fmt: skip
    """Close times of losing trades -> end of the latest pause, or None if the brake never fired.

    Same meaning as StoplossGuard: when a losing trade closes at t and the window [t - lookback, t]
    holds >= limit losing closes, no new entries until t + pause.
    """
    times = sorted(loss_times)
    until = None
    for i, t in enumerate(times):
        in_window = sum(1 for u in times[: i + 1] if u >= t - lookback)
        if in_window >= limit and (until is None or t + pause > until):
            until = t + pause
    return until


class TrendEmaVolTargetLossGuard(TrendEmaVolTarget):
    """VolTarget + R9's numbers counting every losing exit, not only stops (T113)."""

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float, time_in_force: str,
                            current_time: datetime, entry_tag: str | None, side: str, **kwargs) -> bool:  # fmt: skip
        if not super().confirm_trade_entry(pair, order_type, amount, rate, time_in_force, current_time, entry_tag, side, **kwargs):
            return False  # kill switch / stale data first
        since = current_time - LOSS_GUARD_LOOKBACK - LOSS_GUARD_PAUSE  # older losses cannot lock now
        losses = [t.close_date_utc for t in Trade.get_trades_proxy(is_open=False)
                  if (t.close_profit or 0.0) < 0 and t.close_date_utc >= since]  # fmt: skip
        until = loss_guard_until(losses)
        if until is not None and current_time < until:
            _guard_log.warning("LOSSGUARD: %s refused, %d losing exits in 24h, paused until %s", pair, LOSS_GUARD_LIMIT, until)
            return False
        return True


# T114. Textbook volume confirmation (Murphy: volume should confirm the trend): a cross on
# rising participation is more trustworthy than one on a quiet candle. 20 = the fast EMA's window.
VOLUME_WINDOW = 20


def volume_confirmed(volume: pd.Series, window: int = VOLUME_WINDOW) -> pd.Series:
    """True where this candle's volume is above the mean of the PREVIOUS `window` candles."""
    return volume > volume.shift(1).rolling(window).mean()


class TrendEmaVolTargetVolConfirm(TrendEmaVolTarget):
    """VolTarget that only enters when the signal candle's volume beats the previous 20 (T114)."""

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if "enter_long" in dataframe:
            dataframe.loc[~volume_confirmed(dataframe["volume"]), ["enter_long", "enter_tag"]] = (0, None)
        return dataframe


# T132. T115 found EMA 20/50 is a local peak on a rugged surface (neighbours 0.67-1.88), so the
# rule should not hang on one pair: all 9 pairs of the 3x3 grid vote. Enter when the vote turns
# into a majority (>= 5 of 9) with the close above EMA200; exit when the majority is clearly lost
# (<= 3); at 4 the trade is held (hysteresis). Size, stop and protections = TrendEmaVolTarget.
# The first candle has no previous vote, so it is never an event (shift fill_value=True).
VOTE_PAIRS = [(f, s) for f in (15, 20, 25) for s in (40, 50, 60)]
VOTE_ENTER = 5
VOTE_EXIT = 3


def ema_votes(close: pd.Series, pairs: list[tuple[int, int]] = VOTE_PAIRS) -> pd.Series:
    """How many (fast, slow) pairs have fast EMA above slow EMA, per candle."""
    from trend_ema import ema

    return sum((ema(close, f) > ema(close, s)).astype(int) for f, s in pairs)


class TrendEmaVolTargetVote9(TrendEmaVolTarget):
    """VolTarget whose entry/exit signal is a 9-pair EMA vote with hysteresis (T132)."""

    vote_enter = VOTE_ENTER
    vote_exit = VOTE_EXIT

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["votes"] = ema_votes(dataframe["close"])
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        up = dataframe["votes"] >= self.vote_enter
        dataframe.loc[
            up & ~up.shift(1, fill_value=True) & (dataframe["close"] > dataframe["ema_trend"]) & (dataframe["volume"] > 0),
            ["enter_long", "enter_tag"],
        ] = (1, "votes_up")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        down = dataframe["votes"] <= self.vote_exit
        dataframe.loc[
            down & ~down.shift(1, fill_value=True) & (dataframe["volume"] > 0),
            ["exit_long", "exit_tag"],
        ] = (1, "votes_down")
        return dataframe


# T132 robustness neighbours (NOT candidates): only the vote thresholds move, the gap stays 2.
class VTVote4x2(TrendEmaVolTargetVote9):
    vote_enter, vote_exit = 4, 2


class VTVote6x4(TrendEmaVolTargetVote9):
    vote_enter, vote_exit = 6, 4


# T135. LeBeau's chandelier exit (highest price since entry - 3 x ATR(22)), but only once the
# trade has been +1R in profit (1R = the 8% stop distance): T003 trailed from the entry and was
# cut by chop; here the trail only protects winners. EMA exit and the -8% stop are unchanged.
CHANDELIER_ATR = 22
CHANDELIER_MULT = 3.0


def chandelier_exit(open_rate: float, max_rate: float, close: float, atr_value: float,
                    stop: float, mult: float = CHANDELIER_MULT) -> bool:  # fmt: skip
    """True when the trade has reached +1R (= |stop|) and the close fell below max - mult x ATR."""
    if not (atr_value > 0) or max_rate < open_rate * (1 + abs(stop)):
        return False
    return close < max_rate - mult * atr_value


class TrendEmaVolTargetChandelier(TrendEmaVolTarget):
    """VolTarget + a chandelier trailing exit that only starts after +1R (T135)."""

    chandelier_mult = CHANDELIER_MULT

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["atr22"] = atr(dataframe, CHANDELIER_ATR)
        return dataframe

    def custom_exit(self, pair: str, trade, current_time: datetime, current_rate: float, current_profit: float, **kwargs):
        dp = getattr(self, "dp", None)
        if dp is None:
            return None
        dataframe, _ = dp.get_analyzed_dataframe(pair, self.timeframe)  # trimmed to now in backtests
        if dataframe is None or dataframe.empty:
            return None
        last = dataframe.iloc[-1]
        high = max(trade.max_rate or trade.open_rate, trade.open_rate)
        if chandelier_exit(trade.open_rate, high, float(last["close"]), float(last["atr22"]), self.stoploss, self.chandelier_mult):
            return "chandelier"
        return None


# T136. T060/T109/T135 showed that cutting winners early hurts this rule; this tests the opposite.
# Until the trade has been +1R (+8%, the stop distance) the exit is the normal EMA20/EMA50 cross.
# After that the cross is refused and the trade runs until a close below a slower EMA (100).
# The -8% stop never changes. Neighbours 75/150 are part of the same pre-registration.
LETRUN_EMA = 100


def reached_one_r(open_rate: float, max_rate: float | None, stop: float) -> bool:
    """Has the price been at least |stop| above the entry since the trade opened?"""
    return max(max_rate or open_rate, open_rate) >= open_rate * (1 + abs(stop))


class TrendEmaVolTargetLetRun(TrendEmaVolTarget):
    """VolTarget that lets +1R winners run to a close below EMA100 instead of the EMA cross (T136)."""

    letrun_ema = LETRUN_EMA

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        from trend_ema import ema

        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["ema_letrun"] = ema(dataframe["close"], self.letrun_ema)
        return dataframe

    def confirm_trade_exit(self, pair: str, trade, order_type: str, amount: float, rate: float, time_in_force: str,
                           exit_reason: str, current_time: datetime, **kwargs) -> bool:  # fmt: skip
        if exit_reason == "ema_cross_down" and reached_one_r(trade.open_rate, trade.max_rate, self.stoploss):
            return False  # a +1R winner: only the slower EMA (or the stop) ends it
        return True

    def custom_exit(self, pair: str, trade, current_time: datetime, current_rate: float, current_profit: float, **kwargs):
        if not reached_one_r(trade.open_rate, trade.max_rate, self.stoploss):
            return None
        dp = getattr(self, "dp", None)
        if dp is None:
            return None
        dataframe, _ = dp.get_analyzed_dataframe(pair, self.timeframe)  # trimmed to now in backtests
        if dataframe is None or dataframe.empty:
            return None
        last = dataframe.iloc[-1]
        if last["close"] < last["ema_letrun"]:
            return f"letrun_ema{self.letrun_ema}"
        return None


# T136 neighbours (part of the pre-registration, not candidates): only the slow EMA moves.
class VTLetRun75(TrendEmaVolTargetLetRun):
    letrun_ema = 75


class VTLetRun150(TrendEmaVolTargetLetRun):
    letrun_ema = 150


# T139 (research only, a risk-number change: R5 says at most 3 open trades). Same code as
# TrendEmaVolTarget; the 5 slots come from user_data/config/research-max5.json, which ft.py adds
# for this strategy only, in its own Freqtrade run. Never in the live config.
class VTMax5(TrendEmaVolTarget):
    pass


# T142. Threshold-free use of the 9-pair vote (T132 moved the fragility into the vote threshold):
# entries and exits are exactly TrendEmaVolTarget's; only the stake is scaled by the share of the
# 9 EMA pairs that point up on the signal candle (at a 20/50 cross the share is at least 1/9).
def vote_share(votes: float, n_pairs: int = len(VOTE_PAIRS)) -> float:
    """Share of pairs that are up, 0..1; unknown (NaN) -> 1.0 so a missing value never shrinks to 0."""
    if not np.isfinite(votes):
        return 1.0
    return min(max(votes / n_pairs, 0.0), 1.0)


class TrendEmaVolTargetVoteSize(TrendEmaVolTarget):
    """VolTarget entries/exits, stake x share of the 9 EMA pairs that are up (T142)."""

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["votes"] = ema_votes(dataframe["close"])
        return dataframe

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float, proposed_stake: float,
                            min_stake: float | None, max_stake: float, leverage: float, entry_tag: str | None,
                            side: str, **kwargs) -> float:  # fmt: skip
        stake = super().custom_stake_amount(pair, current_time, current_rate, proposed_stake, min_stake, max_stake,
                                            leverage, entry_tag, side, **kwargs)  # fmt: skip
        votes = float("nan")
        dp = getattr(self, "dp", None)
        if dp is not None:
            dataframe, _ = dp.get_analyzed_dataframe(pair, self.timeframe)
            if dataframe is not None and not dataframe.empty and "votes" in dataframe:
                votes = float(dataframe["votes"].iloc[-1])
        return stake * vote_share(votes)


# T143 (volume family). Granville's On-Balance Volume: add the candle's volume when the close rose,
# subtract it when it fell. The entry's trend filter "close > EMA200" becomes "OBV > EMA200 of OBV"
# (same span and method, only the source moves from price to volume). Everything else = VolTarget.
OBV_TREND = 200


def obv(dataframe: DataFrame) -> pd.Series:
    """On-Balance Volume: cumulative volume signed by the close-to-close direction (flat close = 0)."""
    direction = np.sign(dataframe["close"].diff()).fillna(0.0)
    return (direction * dataframe["volume"]).cumsum()


class TrendEmaVolTargetObv(TrendEmaVolTarget):
    """VolTarget whose entry trend filter is OBV above its EMA200 instead of price above EMA200 (T143)."""

    obv_trend = OBV_TREND

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        from trend_ema import ema

        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["obv"] = obv(dataframe)
        dataframe["obv_trend"] = ema(dataframe["obv"], self.obv_trend)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        from trend_ema import crossed_above

        dataframe.loc[
            crossed_above(dataframe["ema_fast"], dataframe["ema_slow"])
            & (dataframe["obv"] > dataframe["obv_trend"])
            & (dataframe["volume"] > 0),
            ["enter_long", "enter_tag"],
        ] = (1, "ema_cross_up_obv")
        return dataframe


# T143 neighbours (only run if T143 passes T110+): only the OBV EMA length moves.
class VTObv150(TrendEmaVolTargetObv):
    obv_trend = 150


class VTObv250(TrendEmaVolTargetObv):
    obv_trend = 250


# T144 (volume family, participation regime): is interest in the coin rising? Enter only when the
# mean volume of the last 7 days beats the last 30 days, both up to the PREVIOUS candle.
PARTIC_SHORT = 24 * 7
PARTIC_LONG = 24 * 30


def participation_rising(volume: pd.Series, short: int = PARTIC_SHORT, long: int = PARTIC_LONG) -> pd.Series:
    prev = volume.shift(1)
    return prev.rolling(short).mean() > prev.rolling(long).mean()


class TrendEmaVolTargetPartic(TrendEmaVolTarget):
    """VolTarget that only enters while the coin's 7-day volume is above its 30-day volume (T144)."""

    partic_short = PARTIC_SHORT

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if "enter_long" in dataframe:
            ok = participation_rising(dataframe["volume"], self.partic_short)
            dataframe.loc[~ok, ["enter_long", "enter_tag"]] = (0, None)
        return dataframe


# T144 neighbours (only run if T144 passes T110+): only the short window moves.
class VTPartic3d(TrendEmaVolTargetPartic):
    partic_short = 24 * 3


class VTPartic14d(TrendEmaVolTargetPartic):
    partic_short = 24 * 14


# T145 (sentiment family). No new entries the day after an "extreme fear" reading (alternative.me's
# own band 0-24): rallies in extreme fear are mostly bounces inside a falling market (the chop the
# final test died in). T021 tested the greed side on TrendEma. Previous UTC day only (no lookahead);
# a day without data allows the entry.
FEAR_MAX = 24

# Imported at module load on purpose: Freqtrade puts this folder on sys.path only while it loads
# the strategy file, so a sibling module imported later inside a method is not found.
from trend_sentiment import fng_for_candles, load_fear_greed  # noqa: E402


class TrendEmaVolTargetFearBlock(TrendEmaVolTarget):
    """VolTarget that skips entries the day after an extreme-fear Fear & Greed reading (T145)."""

    fear_max = FEAR_MAX

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["fng"] = fng_for_candles(dataframe["date"], load_fear_greed())
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if "enter_long" in dataframe:
            fearful = dataframe["fng"] <= self.fear_max  # NaN (no data) -> False -> allowed
            dataframe.loc[fearful, ["enter_long", "enter_tag"]] = (0, None)
        return dataframe


# T145 neighbours (only run if T145 passes T110+): only the fear threshold moves.
class VTFear19(TrendEmaVolTargetFearBlock):
    fear_max = 19


class VTFear29(TrendEmaVolTargetFearBlock):
    fear_max = 29


# T146 (sentiment as an exit, decided once by the coordinator; prior written down: weak, because
# exits that cut winners early hurt this rule three times). Close an open trade the day after an
# extreme-fear reading (<= 24). No data -> no exit. Entries, EMA exit and stop = VolTarget.
class TrendEmaVolTargetFearExit(TrendEmaVolTarget):
    """VolTarget that also leaves open trades the day after an extreme-fear Fear & Greed reading (T146)."""

    fear_max = FEAR_MAX

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["fng"] = fng_for_candles(dataframe["date"], load_fear_greed())
        return dataframe

    def custom_exit(self, pair: str, trade, current_time: datetime, current_rate: float, current_profit: float, **kwargs):
        dp = getattr(self, "dp", None)
        if dp is None:
            return None
        dataframe, _ = dp.get_analyzed_dataframe(pair, self.timeframe)  # trimmed to now in backtests
        if dataframe is None or dataframe.empty or "fng" not in dataframe:
            return None
        if dataframe["fng"].iloc[-1] <= self.fear_max:  # NaN -> False -> stay
            return "fear_exit"
        return None


# T146 neighbours (only run if T146 passes T110+).
class VTFearExit19(TrendEmaVolTargetFearExit):
    fear_max = 19


class VTFearExit29(TrendEmaVolTargetFearExit):
    fear_max = 29


# T147 (attention, late-euphoria hypothesis like T144): no new entries the day after the English
# Wikipedia "Bitcoin" article was read more than 3x its median of the 30 days before. Market-wide
# (per-coin articles are unreliable, docs/research/13). Data: scripts/attention.py. A day's flag is
# only used from the NEXT UTC day on (fng_for_candles); no data -> allowed.
WIKI_FILE = Path(__file__).resolve().parent.parent / "data" / "external" / "wiki_bitcoin.json"
WIKI_SPIKE = 3.0
WIKI_WINDOW = 30


def load_daily_json(path: Path) -> pd.Series:
    """{"YYYY-MM-DD": number} -> Series indexed by UTC day; empty if the file is missing."""
    if not path.exists():
        return pd.Series(dtype=float)
    days = json.loads(path.read_text())
    return pd.Series(list(days.values()), index=pd.to_datetime(list(days.keys()), utc=True), dtype=float).sort_index()


def spike_days(views: pd.Series, mult: float = WIKI_SPIKE, window: int = WIKI_WINDOW) -> pd.Series:
    """1.0 on days whose value is above mult x the median of the `window` days BEFORE it, else 0.0
    (NaN while there is not a full window of history)."""
    base = views.shift(1).rolling(window).median()
    out = (views > mult * base).astype(float)
    return out.where(base.notna())


class TrendEmaVolTargetWikiSpike(TrendEmaVolTarget):
    """VolTarget that skips entries the day after a Bitcoin Wikipedia attention spike (T147)."""

    spike_mult = WIKI_SPIKE

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        views = load_daily_json(WIKI_FILE)
        if views.empty:
            logging.getLogger(__name__).warning("Wikipedia file %s missing: filter OFF (run scripts/attention.py).", WIKI_FILE)
        dataframe["wiki_spike"] = fng_for_candles(dataframe["date"], spike_days(views, self.spike_mult))
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if "enter_long" in dataframe:
            dataframe.loc[dataframe["wiki_spike"] == 1.0, ["enter_long", "enter_tag"]] = (0, None)  # NaN -> allowed
        return dataframe


# T147 neighbours (only run if T147 passes T110+).
class VTWikiSpike2x(TrendEmaVolTargetWikiSpike):
    spike_mult = 2.0


class VTWikiSpike4x(TrendEmaVolTargetWikiSpike):
    spike_mult = 4.0


# T148/T149 (coin data, docs/research/14): market-wide BTC on-chain values from Coin Metrics
# (scripts/onchain.py). A day's value is only used from the NEXT UTC day on (fng_for_candles).
CM_FILE = Path(__file__).resolve().parent.parent / "data" / "external" / "cm_btc.json"
ADR_SHORT, ADR_LONG = 30, 365  # days
MVRV_MAX = 3.7  # Mahmudov & Puell (2018): above 3.7 = the distribution / top zone


def load_cm_metric(metric: str, path: Path | None = None) -> pd.Series:
    """{"metric": {"YYYY-MM-DD": value}} -> daily Series for one metric; empty if the file is missing."""
    path = path or CM_FILE
    if not path.exists():
        return pd.Series(dtype=float)
    days = json.loads(path.read_text()).get(metric, {})
    return pd.Series(list(days.values()), index=pd.to_datetime(list(days.keys()), utc=True), dtype=float).sort_index()


def adr_rising(adr: pd.Series, short: int = ADR_SHORT, long: int = ADR_LONG) -> pd.Series:
    """1.0 on days whose short mean of active addresses beats the long mean (both up to that day), else 0.0;
    NaN until a full long window exists."""
    s, l_ = adr.rolling(short).mean(), adr.rolling(long).mean()
    return (s > l_).astype(float).where(l_.notna())


class TrendEmaVolTargetAdrTrend(TrendEmaVolTarget):
    """VolTarget that only enters while BTC network use (active addresses) is trending up (T148)."""

    adr_short = ADR_SHORT

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["adr_up"] = fng_for_candles(dataframe["date"], adr_rising(load_cm_metric("AdrActCnt"), self.adr_short))
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if "enter_long" in dataframe:
            dataframe.loc[dataframe["adr_up"] == 0.0, ["enter_long", "enter_tag"]] = (0, None)  # NaN -> allowed
        return dataframe


class VTAdrTrend15(TrendEmaVolTargetAdrTrend):
    adr_short = 15


class VTAdrTrend60(TrendEmaVolTargetAdrTrend):
    adr_short = 60


class TrendEmaVolTargetMvrvBlock(TrendEmaVolTarget):
    """VolTarget that skips entries the day after BTC MVRV was above 3.7 (T149)."""

    mvrv_max = MVRV_MAX

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["mvrv"] = fng_for_candles(dataframe["date"], load_cm_metric("CapMVRVCur"))
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if "enter_long" in dataframe:
            dataframe.loc[dataframe["mvrv"] > self.mvrv_max, ["enter_long", "enter_tag"]] = (0, None)  # NaN -> allowed
        return dataframe


class VTMvrv32(TrendEmaVolTargetMvrvBlock):
    mvrv_max = 3.2


class VTMvrv42(TrendEmaVolTargetMvrvBlock):
    mvrv_max = 4.2


# T151 ("don't chase"): the EMA cross sometimes comes right after a spike candle; buying when the
# close is already far above the short mean is a classic whipsaw entry. Skip the entry when the
# close is more than 2 x ATR(14) above EMA20 (the textbook Keltner band). Everything else = VolTarget.
CHASE_ATR = 14
CHASE_MULT = 2.0


def too_extended(dataframe: DataFrame, mult: float = CHASE_MULT) -> pd.Series:
    """True where close - EMA20 is above mult x ATR(14) on the same candle (no future values used)."""
    return (dataframe["close"] - dataframe["ema_fast"]) > mult * atr(dataframe, CHASE_ATR)


class TrendEmaVolTargetNoChase(TrendEmaVolTarget):
    """VolTarget that skips entries when price is stretched more than 2 ATR above EMA20 (T151)."""

    chase_mult = CHASE_MULT

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if "enter_long" in dataframe:
            dataframe.loc[too_extended(dataframe, self.chase_mult), ["enter_long", "enter_tag"]] = (0, None)
        return dataframe


# T151 neighbours (only run if T151 passes T110+).
class VTNoChase15(TrendEmaVolTargetNoChase):
    chase_mult = 1.5


class VTNoChase25(TrendEmaVolTargetNoChase):
    chase_mult = 2.5


# T152: no new entries whose signal candle falls on a weekend (UTC): thinner weekend liquidity and
# more false crosses (day-of-week effect, Caporale & Plastun 2019). Exits unchanged.
WEEKEND = (5, 6)  # Saturday, Sunday (pandas dayofweek)


class TrendEmaVolTargetNoWeekend(TrendEmaVolTarget):
    """VolTarget that skips entries signalled on Saturday/Sunday UTC (T152)."""

    skip_days = WEEKEND

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if "enter_long" in dataframe:
            dataframe.loc[dataframe["date"].dt.dayofweek.isin(self.skip_days), ["enter_long", "enter_tag"]] = (0, None)
        return dataframe


class VTNoSunday(TrendEmaVolTargetNoWeekend):  # T152 neighbour (only run if T152 passes)
    skip_days = (6,)


# T153: when BTC's 1h close crosses below BTC's EMA200, every non-BTC open trade gets an exit
# signal (altcoins follow BTC breakdowns). Entries unchanged. BTC is merged by date only, so each
# candle sees BTC's value at the same moment (no lookahead); declared as an informative pair for live.
BTC_EXIT_EMA = 200


def btc_cross_down(btc: DataFrame, length: int = BTC_EXIT_EMA) -> DataFrame:
    """date -> True on the BTC candle whose close crosses below its EMA(length)."""
    from trend_ema import crossed_below, ema

    out = DataFrame({"date": btc["date"]})
    out["btc_break"] = crossed_below(btc["close"], ema(btc["close"], length)).astype(bool)
    return out


class TrendEmaVolTargetBtcExit(TrendEmaVolTarget):
    """VolTarget + exit all non-BTC trades when BTC closes below its EMA200 (T153)."""

    btc_ema = BTC_EXIT_EMA

    def informative_pairs(self):
        return [("BTC/USDT", self.timeframe)]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        btc = self.dp.get_pair_dataframe("BTC/USDT", self.timeframe) if getattr(self, "dp", None) else None
        if btc is None or btc.empty:
            dataframe["btc_break"] = False
            return dataframe
        merged = dataframe[["date"]].merge(btc_cross_down(btc, self.btc_ema), on="date", how="left")
        dataframe["btc_break"] = merged["btc_break"].fillna(False).astype(bool).to_numpy()
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_exit_trend(dataframe, metadata)
        if metadata.get("pair", "").startswith("BTC/"):
            return dataframe
        hit = dataframe["btc_break"] & (dataframe.get("exit_long", 0) != 1) & (dataframe["volume"] > 0)
        dataframe.loc[hit, ["exit_long", "exit_tag"]] = (1, "btc_breakdown")
        return dataframe


class VTBtcExit150(TrendEmaVolTargetBtcExit):  # T153 neighbours (only run if T153 passes)
    btc_ema = 150


class VTBtcExit250(TrendEmaVolTargetBtcExit):
    btc_ema = 250


# T154 (funding rate, read only: we still trade spot). A high perpetual funding rate means crowded
# leveraged longs. Skip entries when the coin's latest rate known at the candle's open is above the
# 90th percentile of its previous 270 rates (90 days of 8h rates). No data or warm-up -> filter off.
# An "extreme moment" filter: per docs/research/15 the prior is low. Data: scripts/funding.py.
FUNDING_DIR = Path(__file__).resolve().parent.parent / "data" / "external"
FUNDING_WINDOW = 270
FUNDING_QUANTILE = 0.90


def load_funding(coin: str, folder: Path | None = None) -> pd.Series:
    """{"fundingTime ms": rate} -> Series indexed by UTC time, oldest first; empty if there is no file."""
    path = (folder or FUNDING_DIR) / f"funding_{coin}.json"
    if not path.exists():
        return pd.Series(dtype=float)
    days = json.loads(path.read_text())
    idx = pd.to_datetime([int(k) for k in days], unit="ms", utc=True)
    return pd.Series(list(days.values()), index=idx, dtype=float).sort_index()


def crowded_flags(rates: pd.Series, q: float = FUNDING_QUANTILE, window: int = FUNDING_WINDOW) -> pd.Series:
    """1.0 where a rate is above the q-quantile of the `window` rates BEFORE it, else 0.0; NaN in warm-up."""
    limit = rates.shift(1).rolling(window).quantile(q)
    return (rates > limit).astype(float).where(limit.notna())


def crowded_at(dates: pd.Series, flags: pd.Series) -> pd.Series:
    """For each candle: the flag of the last funding time <= the candle's open (NaN if none)."""
    if flags.empty:
        return pd.Series(np.nan, index=dates.index)
    left = pd.DataFrame({"date": pd.to_datetime(dates, utc=True).astype("datetime64[ns, UTC]"), "i": dates.index})
    right = pd.DataFrame({"t": flags.index.astype("datetime64[ns, UTC]"), "crowded": flags.to_numpy()})
    merged = pd.merge_asof(left.sort_values("date"), right.sort_values("t"), left_on="date", right_on="t", direction="backward")
    return merged.set_index("i")["crowded"].reindex(dates.index)


class TrendEmaVolTargetFunding(TrendEmaVolTarget):
    """VolTarget that skips entries while the coin's perpetual funding says longs are crowded (T154)."""

    funding_q = FUNDING_QUANTILE

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        coin = metadata.get("pair", "").split("/")[0]
        dataframe["crowded"] = crowded_at(dataframe["date"], crowded_flags(load_funding(coin), self.funding_q))
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if "enter_long" in dataframe:
            dataframe.loc[dataframe["crowded"] == 1.0, ["enter_long", "enter_tag"]] = (0, None)  # NaN -> allowed
        return dataframe


# T154 neighbours (only run if T154 passes T110+).
class VTFunding80(TrendEmaVolTargetFunding):
    funding_q = 0.80


class VTFunding95(TrendEmaVolTargetFunding):
    funding_q = 0.95


# T155 (slow liquidity regime, not an extreme-moment filter): new stablecoin issuance means fresh
# dollars entering crypto. Enter only while total USDT + USDC supply is higher than 30 days before,
# using the previous UTC day's value (fng_for_candles). Market-wide; no data -> allowed.
# Data: scripts/onchain.py (Coin Metrics Community, CC BY-NC).
STABLE_FILE = Path(__file__).resolve().parent.parent / "data" / "external" / "cm_stable.json"
STABLE_DAYS = 30


def stable_total(path: Path | None = None) -> pd.Series:
    """{asset: {day: supply}} -> total supply per calendar day (gaps carried forward, an asset counts
    0 before its first day); empty if the file is missing."""
    path = path or STABLE_FILE
    if not path.exists():
        return pd.Series(dtype=float)
    parts = []
    for days in json.loads(path.read_text()).values():
        s = pd.Series(list(days.values()), index=pd.to_datetime(list(days.keys()), utc=True), dtype=float).sort_index()
        parts.append(s)
    if not parts:
        return pd.Series(dtype=float)
    full = pd.date_range(min(s.index[0] for s in parts), max(s.index[-1] for s in parts), freq="D", tz="UTC")
    return sum(s.reindex(full).ffill().fillna(0.0) for s in parts)


def stable_growing(total: pd.Series, days: int = STABLE_DAYS) -> pd.Series:
    """1.0 on days whose total beats the total `days` days earlier, else 0.0; NaN without that history."""
    before = total.shift(days)
    return (total > before).astype(float).where(before.notna())


class TrendEmaVolTargetStableFlow(TrendEmaVolTarget):
    """VolTarget that only enters while stablecoin supply has grown over the last 30 days (T155)."""

    stable_days = STABLE_DAYS

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["stable_up"] = fng_for_candles(dataframe["date"], stable_growing(stable_total(), self.stable_days))
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if "enter_long" in dataframe:
            dataframe.loc[dataframe["stable_up"] == 0.0, ["enter_long", "enter_tag"]] = (0, None)  # NaN -> allowed
        return dataframe


class VTStableFlow14(TrendEmaVolTargetStableFlow):  # T155 neighbours (only run if T155 passes)
    stable_days = 14


class VTStableFlow60(TrendEmaVolTargetStableFlow):
    stable_days = 60


# T158 Hash Ribbons (Charles Edwards, Capriole): BTC hash rate's 30-day mean below its 60-day mean
# means miners are under stress. No new entries during that stress; exits unchanged. Slow,
# market-wide regime. Previous UTC day only (fng_for_candles); no data -> allowed.
RIBBON_FAST, RIBBON_SLOW = 30, 60


def miner_stress(hash_rate: pd.Series, fast: int = RIBBON_FAST, slow: int = RIBBON_SLOW) -> pd.Series:
    """1.0 on days whose fast SMA of hash rate is below the slow SMA, else 0.0; NaN until both exist."""
    f, s = hash_rate.rolling(fast).mean(), hash_rate.rolling(slow).mean()
    return (f < s).astype(float).where(s.notna())


class TrendEmaVolTargetHashRibbon(TrendEmaVolTarget):
    """VolTarget that skips entries while BTC miners are under stress (hash rate SMA30 < SMA60) (T158)."""

    ribbon = (RIBBON_FAST, RIBBON_SLOW)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["miner_stress"] = fng_for_candles(dataframe["date"], miner_stress(load_cm_metric("HashRate"), *self.ribbon))
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if "enter_long" in dataframe:
            dataframe.loc[dataframe["miner_stress"] == 1.0, ["enter_long", "enter_tag"]] = (0, None)  # NaN -> allowed
        return dataframe


class VTHashRibbon2050(TrendEmaVolTargetHashRibbon):  # T158 neighbours (only run if T158 passes)
    ribbon = (20, 50)


class VTHashRibbon4080(TrendEmaVolTargetHashRibbon):
    ribbon = (40, 80)


# T159: a slow attention regime (T147 was the extreme-moment version). Enter only while the 30-day
# mean of the Bitcoin Wikipedia pageviews is at or above its 90-day mean, using the previous UTC
# day (fng_for_candles); no data -> allowed. Relatives T144 (volume) and T148 (addresses) failed.
ATTN_FAST, ATTN_SLOW = 30, 90


def attention_rising(views: pd.Series, fast: int = ATTN_FAST, slow: int = ATTN_SLOW) -> pd.Series:
    """1.0 on days whose fast mean of pageviews is >= the slow mean, else 0.0; NaN until both exist."""
    f, s = views.rolling(fast).mean(), views.rolling(slow).mean()
    return (f >= s).astype(float).where(s.notna())


class TrendEmaVolTargetAttnTrend(TrendEmaVolTarget):
    """VolTarget that only enters while public attention to Bitcoin is slowly rising (T159)."""

    attn = (ATTN_FAST, ATTN_SLOW)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["attn_up"] = fng_for_candles(dataframe["date"], attention_rising(load_daily_json(WIKI_FILE), *self.attn))
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if "enter_long" in dataframe:
            dataframe.loc[dataframe["attn_up"] == 0.0, ["enter_long", "enter_tag"]] = (0, None)  # NaN -> allowed
        return dataframe


class VTAttnTrend2060(TrendEmaVolTargetAttnTrend):  # T159 neighbours (only run if T159 passes)
    attn = (20, 60)


class VTAttnTrend45135(TrendEmaVolTargetAttnTrend):
    attn = (45, 135)


# T162 ("altcoin season", a selection rule): non-BTC entries only while BTC's share of the market
# value of BTC+ETH+XRP+BNB is lower than 30 days before (money moving from BTC into altcoins).
# BTC itself is always allowed. Previous UTC day only; no data -> allowed. Data: scripts/onchain.py.
CAPS_FILE = Path(__file__).resolve().parent.parent / "data" / "external" / "cm_caps.json"
BTCDOM_DAYS = 30


def btc_share(path: Path | None = None) -> pd.Series:
    """Daily BTC cap / (sum of all caps in the file), only on days where every asset has a value."""
    path = path or CAPS_FILE
    if not path.exists():
        return pd.Series(dtype=float)
    raw = json.loads(path.read_text())
    df = DataFrame({a: pd.Series(list(v.values()), index=pd.to_datetime(list(v.keys()), utc=True), dtype=float)
                    for a, v in raw.items()}).sort_index().dropna()  # fmt: skip
    if df.empty or "btc" not in df:
        return pd.Series(dtype=float)
    return df["btc"] / df.sum(axis=1)


def btc_losing_share(share: pd.Series, days: int = BTCDOM_DAYS) -> pd.Series:
    """1.0 on days whose BTC share is below the share `days` calendar days earlier, else 0.0; NaN without history."""
    if share.empty:
        return share
    daily = share.asfreq("D").ffill()
    before = daily.shift(days)
    return (daily < before).astype(float).where(before.notna())


class TrendEmaVolTargetBtcDom(TrendEmaVolTarget):
    """VolTarget that buys altcoins only while BTC is losing market share (T162); BTC always allowed."""

    dom_days = BTCDOM_DAYS

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["alt_season"] = fng_for_candles(dataframe["date"], btc_losing_share(btc_share(), self.dom_days))
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if "enter_long" in dataframe and not metadata.get("pair", "").startswith("BTC/"):
            dataframe.loc[dataframe["alt_season"] == 0.0, ["enter_long", "enter_tag"]] = (0, None)  # NaN -> allowed
        return dataframe


class VTBtcDom14(TrendEmaVolTargetBtcDom):  # T162 neighbours (only run if T162 passes)
    dom_days = 14


class VTBtcDom60(TrendEmaVolTargetBtcDom):
    dom_days = 60
