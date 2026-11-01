"""3Commas-style DCA bot simulator (research benchmark, spot only).

How such a bot works, in plain words:
  1. Open a "deal": buy a small base order right away.
  2. If the price falls, buy more at preset steps below ("safety orders"),
     each one bigger than the last. This pulls the average buy price down.
  3. As soon as selling would earn `TAKE_PROFIT` over everything spent (fees included), sell
     everything. Then start a new deal immediately.
  There is no stop-loss (the default on 3Commas). If the price falls below
  the last safety order, the bot just waits, possibly for months.

Settings: a typical "classic" long DCA setup as described in 3Commas' public
help pages. Written before seeing any result and NOT tuned:
  take profit 1.5%, 5 safety orders, first one 2% below the start,
  step scale 1.5 (each gap 1.5x the previous), volume scale 1.5 (each order
  1.5x the previous), safety order 1 = base order size.
  -> safety orders at -2%, -5%, -9.5%, -16.25%, -26.4% from the deal start.

Fill model on 1h candles: take profit is checked first (high reaches the
target), then safety orders (low reaches the level). A deal opened on a
candle's close can only be closed from the next candle.
"""

import numpy as np
import pandas as pd

from benchmark import DEFAULT_FEE

TAKE_PROFIT = 0.015
SAFETY_ORDERS = 5
FIRST_DEVIATION = 0.02
STEP_SCALE = 1.5
VOLUME_SCALE = 1.5


def ladder(
    n: int = SAFETY_ORDERS, first: float = FIRST_DEVIATION, step: float = STEP_SCALE, volume: float = VOLUME_SCALE
) -> tuple[np.ndarray, np.ndarray]:
    """Drop from deal start for each safety order, and each order's size (base order = 1)."""
    gaps = first * step ** np.arange(n)
    drops = np.cumsum(gaps)
    sizes = np.concatenate([[1.0], volume ** np.arange(n)])  # base, SO1 = base, then x1.5 each
    return drops, sizes


def simulate_pair(candles: pd.DataFrame, cash: float, fee: float = DEFAULT_FEE) -> tuple[pd.Series, int]:
    """Equity of one coin's DCA bot at every candle close, and the number of finished deals."""
    high, low, close = (candles[c].to_numpy() for c in ("high", "low", "close"))
    drops, sizes = ladder()
    unit = cash / sizes.sum()  # the full ladder uses exactly this coin's cash
    coins = spent = 0.0
    start = None  # deal start price; None = no open deal
    next_so = 0
    deals = 0
    equity = np.empty(len(close))
    for i in range(len(close)):
        if start is not None:
            # 1) take profit on the average price (fees included in `spent`)
            target = spent / (coins * (1 - fee)) * (1 + TAKE_PROFIT)
            if high[i] >= target:
                cash += coins * target * (1 - fee)
                coins = spent = 0.0
                start = None
                deals += 1
            else:
                # 2) safety orders the candle's low reached
                while next_so < len(drops) and low[i] <= start * (1 - drops[next_so]):
                    price = start * (1 - drops[next_so])
                    amount = min(unit * sizes[next_so + 1], cash)
                    coins += amount * (1 - fee) / price
                    spent += amount
                    cash -= amount
                    next_so += 1
        if start is None:
            # 3) start a new deal right away ("ASAP") with the base order
            start = close[i]
            amount = min(unit * sizes[0], cash)
            coins, spent, next_so = amount * (1 - fee) / start, amount, 0
            cash -= amount
        equity[i] = cash + coins * close[i]
    equity[-1] = cash + coins * close[-1] * (1 - fee)
    return pd.Series(equity, index=candles.index), deals
