"""Time-series momentum with volatility scaling (TSMOM), our own code, research only.

A different rule family from TrendEma (moving-average cross on hourly candles):
look at each coin once a day and ask "did it go up over the last 4 weeks?".
If yes, hold it; if no, hold cash. How MUCH to hold depends on how wildly the
coin moves: a calm coin gets more money, a wild one less.

Ideas from published research (only the ideas; the code is ft-lab's own):
  - Moskowitz, Ooi & Pedersen (2012), "Time Series Momentum": the sign of an
    asset's own past 12-month return predicts the next month, across many
    markets. Positions are scaled to 40% annual volatility per asset.
  - Liu & Tsyvinski (2021), "Risks and Returns of Cryptocurrency": for crypto,
    the momentum horizon is short: 1-4 weeks.

Rules, fixed BEFORE seeing any result, textbook values, not tuned:
  every day at 00:00 UTC, using daily closes up to yesterday:
    1. signal: the coin's 28-day return > 0  (Liu & Tsyvinski: 4 weeks)
    2. volatility: standard deviation of the last 30 daily returns, annualized (x sqrt(365))
    3. each coin owns 1/N of the money (N = coins in the group); inside its share
       it holds  min(1, 40% / volatility)  in coins when the signal is on, 0 when off
       (Moskowitz et al.: 40% per asset). Never more than 25% of all money in one
       coin (R4 in docs/risk-rules.md).
    4. To keep fees down, a coin is only traded when its signal flips or its
       wanted share moved by more than 20 percentage points of its 1/N part.
  Spot only, no leverage, no stop-loss (a daily rule; the signal itself exits).

    python3 scripts/ft.py bots --slice train --universe wide   (row "TSMOM")
"""

import numpy as np
import pandas as pd

LOOKBACK_DAYS = 28
VOL_DAYS = 30
TARGET_VOL = 0.40
MAX_WEIGHT = 0.25
BUFFER = 0.20


def target_weights(
    daily: pd.DataFrame,
    lookback: int = LOOKBACK_DAYS,
    vol_days: int = VOL_DAYS,
    target_vol: float = TARGET_VOL,
    max_weight: float = MAX_WEIGHT,
    buffer: float = BUFFER,
) -> pd.DataFrame:
    """Wanted share of ALL money per coin, decided on each day's close (row = that day).

    Only days where at least one coin changes are kept, so the simulator trades
    only then. A coin without enough history has weight 0.
    """
    n = daily.shape[1]
    part = 1.0 / n
    signal = daily / daily.shift(lookback) - 1 > 0
    vol = daily.pct_change(fill_method=None).rolling(vol_days).std() * np.sqrt(365)
    raw = (target_vol / vol).clip(upper=1.0) * part
    raw = raw.where(signal & vol.notna(), 0.0).clip(upper=max_weight).fillna(0.0)

    current = pd.Series(0.0, index=daily.columns)
    rows, days = [], []
    for day, want in raw.iterrows():
        flipped = (want > 0) != (current > 0)
        drifted = (want - current).abs() > buffer * part
        change = flipped | drifted
        if change.any():
            current = current.where(~change, want)
            # NaN = "leave this coin alone today" (no small drift trades, no fees)
            rows.append(want.where(change))
            days.append(day)
    return pd.DataFrame(rows, index=pd.DatetimeIndex(days), columns=daily.columns)


def simulate(hourly: pd.DataFrame, weights: pd.DataFrame, fee: float) -> tuple[pd.Series, int]:
    """Equity (start 1.0) at each hourly close, and the number of buy/sell orders.

    A decision on day D's close is traded at the first hourly candle of D+1.
    Only coins with a number (not NaN) in that row are traded, to that share
    of the portfolio's value at that moment.
    """
    prices = hourly.to_numpy()
    cols = list(hourly.columns)
    apply_at = {d + pd.Timedelta(days=1): w.reindex(cols).to_numpy() for d, w in weights.iterrows()}
    cash, units = 1.0, np.zeros(len(cols))
    equity = np.empty(len(prices))
    orders = 0
    for i, ts in enumerate(hourly.index):
        p = prices[i]
        if ts in apply_at:
            value = cash + np.nansum(units * p)
            w = apply_at[ts]
            todo = ~np.isnan(w) & ~np.isnan(p)
            trade = np.zeros(len(cols))
            trade[todo] = w[todo] * value - units[todo] * p[todo]
            for k in np.flatnonzero(trade < -1e-12):  # sells first, they free cash
                sold = min(-trade[k] / p[k], units[k])
                cash += sold * p[k] * (1 - fee)
                units[k] -= sold
                orders += 1
            for k in np.flatnonzero(trade > 1e-12):
                spend = min(trade[k], cash)
                if spend > 0:
                    units[k] += spend * (1 - fee) / p[k]
                    cash -= spend
                    orders += 1
        equity[i] = cash + np.nansum(units * p)
    equity[-1] = cash + np.nansum(units * prices[-1]) * (1 - fee)  # sell the rest at the end
    return pd.Series(equity, index=hourly.index), orders
