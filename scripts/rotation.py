"""Momentum rotation ("hold the strongest coins"), our own rule, research only.

A different family from TrendEma. TrendEma asks of each coin on its own: "is
this one going up?" Rotation compares the coins with each other once a week:
"which ones went up the most lately?" It holds the strongest few and switches
when the ranking changes.

Ideas from published research (only the ideas; the code is ft-lab's own):
  - Liu & Tsyvinski (2021), "Risks and Returns of Cryptocurrency": crypto
    returns show momentum, so coins that rose in the last weeks tend to keep
    rising a little.
  - Antonacci (2014), "Dual Momentum": hold an asset only if it beats the
    others (relative) AND has itself gone up (absolute); otherwise hold cash.
  - Faber (2007): stay out of the whole market while it is below its long
    average. Here "the market" is BTC.

Rules, fixed BEFORE seeing any result, textbook values, not tuned:
  every Monday 00:00 UTC, using daily closes up to Sunday:
    1. If BTC is below its 100-day average, hold everything in cash.
       (100 days, not 200: our data starts 2020-10, so a 200-day average
       would leave the first half of 2021 empty.)
    2. Score each coin by its return over the last 30 days.
    3. Keep the 4 best scores that are above 0; give each 25% of the money
       (25% = the position cap in docs/risk-rules.md, R4). Unused slots = cash.
  No stop-loss in between (a weekly rule). Fee is paid on every change.

    python3 scripts/ft.py bots --slice train --universe wide   (row "Rotation")
"""

import numpy as np
import pandas as pd

from benchmark import DEFAULT_FEE

LOOKBACK_DAYS = 30
TOP = 4
WEIGHT = 0.25
BTC_SMA_DAYS = 100
REBALANCE = "W-MON"


def daily_closes(hourly: dict[str, pd.Series]) -> pd.DataFrame:
    """Last hourly close of each UTC day, labelled with that day."""
    return pd.DataFrame(hourly).resample("1D").last()


def target_weights(
    daily: pd.DataFrame,
    btc_daily: pd.Series,
    lookback: int = LOOKBACK_DAYS,
    top: int = TOP,
    weight: float = WEIGHT,
    sma_days: int = BTC_SMA_DAYS,
) -> pd.DataFrame:
    """Wanted weight per coin, decided on each Sunday's close (row = that Sunday).

    A coin needs `lookback` days of history to get a score; without one it is skipped.
    """
    score = daily / daily.shift(lookback) - 1
    btc_ok = btc_daily > btc_daily.rolling(sma_days).mean()
    sundays = daily.index[daily.index.day_of_week == 6]
    rows = []
    for day in sundays:
        w = pd.Series(0.0, index=daily.columns)
        if bool(btc_ok.get(day, False)):
            s = score.loc[day].dropna()
            best = s[s > 0].sort_values(ascending=False).head(top)
            w[best.index] = weight
        rows.append(w)
    return pd.DataFrame(rows, index=sundays)


def simulate(
    hourly: pd.DataFrame, weights: pd.DataFrame, fee: float = DEFAULT_FEE
) -> tuple[pd.Series, int]:
    """Equity (start 1.0) at each hourly close, and the number of buy/sell orders.

    A decision made on Sunday's daily close (the 23:00 candle's close) is
    traded at the next candle: Monday 00:00 open = that same close, so we use it.
    """
    prices = hourly.to_numpy()
    cols = list(hourly.columns)
    # decision on day D -> applied at the first hourly candle of D+1
    apply_at = {d + pd.Timedelta(days=1): w.reindex(cols).fillna(0.0).to_numpy() for d, w in weights.iterrows()}
    cash, units = 1.0, np.zeros(len(cols))
    equity = np.empty(len(prices))
    orders = 0
    for i, ts in enumerate(hourly.index):
        p = prices[i]
        if ts in apply_at:
            value = cash + np.nansum(units * p)
            target = apply_at[ts] * value
            target[np.isnan(p)] = 0.0  # no price, no position
            current = np.where(np.isnan(p), 0.0, units * p)
            trade = target - current
            trade[np.abs(trade) < 1e-9] = 0.0
            # sells first (they free the cash for the buys)
            for k in np.flatnonzero(trade < 0):
                cash += -trade[k] * (1 - fee)
                units[k] -= -trade[k] / p[k]
                orders += 1
            for k in np.flatnonzero(trade > 0):
                spend = min(trade[k], cash)
                units[k] += spend * (1 - fee) / p[k]
                cash -= spend
                orders += 1
            units[np.abs(units) < 1e-12] = 0.0
        equity[i] = cash + np.nansum(units * p)
    last = prices[-1]
    equity[-1] = cash + np.nansum(units * last) * (1 - fee)  # sell the rest at the end
    return pd.Series(equity, index=hourly.index), orders
