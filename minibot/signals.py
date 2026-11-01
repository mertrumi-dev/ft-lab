"""TrendEma's rules and VolTarget's sizing, rewritten without Freqtrade (plain Python lists, no pandas).

Same idea as user_data/strategies/trend_ema.py:
    buy  when EMA20 crosses above EMA50 and the close is above EMA200
    sell when EMA20 crosses below EMA50
and user_data/strategies/sizing.py (TrendEmaVolTarget):
    stake = normal stake x min(1, 60% / the coin's annualized volatility of the last 720 hourly returns)
"""

import math
import statistics

FAST, SLOW, TREND = 20, 50, 200
TARGET_VOL = 0.60  # annualized, same number as sizing.py
VOL_WINDOW = 24 * 30  # 720 hourly returns = 30 days
HOURS_PER_YEAR = 24 * 365


def ema(values: list[float], length: int) -> list[float]:
    """Exponential moving average. Same formula as pandas ewm(span=length, adjust=False).

    alpha = 2 / (length + 1). The first value is the first price; then each new
    value moves `alpha` of the way from the old average towards the new price.
    """
    alpha = 2 / (length + 1)
    out: list[float] = []
    for v in values:
        out.append(v if not out else out[-1] + alpha * (v - out[-1]))
    return out


def signal(closes: list[float]) -> str:
    """'buy', 'sell' or 'hold', judged on the LAST closed candle.

    Needs at least 2 x TREND candles so EMA200 has warmed up (same as the strategy).
    """
    if len(closes) < 2 * TREND:
        return "hold"
    fast, slow, trend = ema(closes, FAST), ema(closes, SLOW), ema(closes, TREND)
    crossed_up = fast[-1] > slow[-1] and fast[-2] <= slow[-2]
    crossed_down = fast[-1] < slow[-1] and fast[-2] >= slow[-2]
    if crossed_up and closes[-1] > trend[-1]:
        return "buy"
    if crossed_down:
        return "sell"
    return "hold"


def realized_vol(closes: list[float], window: int = VOL_WINDOW) -> float:
    """Annualized volatility of the last `window` hourly log returns (NaN until there are enough).

    Same as pandas: log(close).diff().rolling(window).std() * sqrt(hours per year),
    where std is the sample standard deviation (divides by n - 1).
    """
    if len(closes) < window + 1:
        return math.nan
    tail = closes[-(window + 1):]
    returns = [math.log(b / a) for a, b in zip(tail, tail[1:])]
    return statistics.stdev(returns) * math.sqrt(HOURS_PER_YEAR)


def vol_scale(vol: float, target: float = TARGET_VOL) -> float:
    """How much of the normal stake to use: 1 for calm coins, less for wild ones (never more than 1)."""
    if not math.isfinite(vol) or vol <= 0:
        return 1.0  # no reading yet: behave like TrendEma
    return min(1.0, target / vol)
