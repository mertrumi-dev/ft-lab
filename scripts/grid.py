"""Grid trading simulator (Phase 4 idea, spot only, research only).

Grid in plain words: put buy orders on a ladder below today's price, every
`step` (e.g. 2%) apart. When a rung is bought, put a sell order one step above
it. Every buy-low / sell-one-step-higher round trip earns about one step minus
fees. If the price climbs above the top of the ladder with nothing bought, the
ladder moves up (a "trailing up" grid). If the price falls below the ladder, we
simply hold what we bought: spot, no leverage, no stop.

Known in advance: grids earn in sideways markets, sell winners too early in
rallies and fill up with falling coins in crashes. We measure how much.

    python3 scripts/ft.py bots --slice train   (table with all bot types)

Fill model on 1h candles: a buy fills if the candle's LOW reaches the rung, a
sell fills if its HIGH reaches the target. Sells are checked before buys, and a
rung bought in a candle cannot be sold in the same candle (we don't know the
order of the high and the low inside the hour, so we assume the worse case).
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from benchmark import DATA_DIR, DEFAULT_FEE  # noqa: E402
from splits import SLICES  # noqa: E402

STEP = 0.02  # 2% between rungs: must be well above 2 x fee (0.3%) to earn anything
LEVELS = 10  # 10 rungs -> the ladder covers about -18% below the anchor


def load_candles(pair: str, slice_name: str, data_dir: Path = DATA_DIR) -> pd.DataFrame:
    s = SLICES[slice_name]
    path = data_dir / f"{pair.replace('/', '_')}-1h.feather"
    df = pd.read_feather(path).set_index("date")
    start, end = pd.Timestamp(s.start, tz="UTC"), pd.Timestamp(s.end, tz="UTC")
    return df[(df.index >= start) & (df.index < end)][["high", "low", "close"]]


def simulate_pair(
    candles: pd.DataFrame, cash: float, step: float = STEP, levels: int = LEVELS, fee: float = DEFAULT_FEE
) -> tuple[pd.Series, int]:
    """Equity of one coin's grid at every candle close, and the number of round trips."""
    high, low, close = (candles[c].to_numpy() for c in ("high", "low", "close"))
    per_rung = cash / levels
    anchor = close[0]
    rungs = anchor * (1 - step) ** np.arange(1, levels + 1)  # buy prices, highest first
    held = np.zeros(levels)  # coins held per rung (0 = rung is waiting to buy)
    equity = np.empty(len(close))
    trips = 0
    for i in range(len(close)):
        # 1) sells: a held rung sells one step above its buy price
        for k in range(levels):
            if held[k] > 0 and high[i] >= rungs[k] * (1 + step):
                cash += held[k] * rungs[k] * (1 + step) * (1 - fee)
                held[k] = 0.0
                trips += 1
        # 2) trailing up: ladder empty and price ran a full step above the anchor
        if not held.any() and close[i] >= anchor * (1 + step):
            anchor = close[i]
            rungs = anchor * (1 - step) ** np.arange(1, levels + 1)
        # 3) buys: an empty rung buys when the low touches it (if cash allows)
        else:
            for k in range(levels):
                if held[k] == 0 and low[i] <= rungs[k] and cash >= per_rung * 0.999:
                    spend = min(per_rung, cash)
                    held[k] = spend * (1 - fee) / rungs[k]
                    cash -= spend
        equity[i] = cash + held.sum() * close[i]
    equity[-1] = cash + held.sum() * close[-1] * (1 - fee)  # sell the rest at the end
    return pd.Series(equity, index=candles.index), trips
