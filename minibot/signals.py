"""TrendEma's rules, rewritten without Freqtrade (plain Python lists, no pandas).

Same idea as user_data/strategies/trend_ema.py:
    buy  when EMA20 crosses above EMA50 and the close is above EMA200
    sell when EMA20 crosses below EMA50
"""

FAST, SLOW, TREND = 20, 50, 200


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
