"""Chart reading for one coin, in numbers (the input for an AI or human chart reading).

    python3 scripts/ft.py chart --pair ETH/USDT

Prints what a trader looks at on a daily chart, computed from the downloaded
candles instead of eyeballed:
  - last close, and its distance to the daily EMA20 / EMA50 / EMA200
  - returns over 7 / 30 / 90 days, and the 60-day high and low
  - nearby support / resistance: recent daily swing lows / highs
  - 30-day volatility (annualized) and volume now vs the last 90 days
  - what OUR bot thinks on 1h candles: trend state, entry signal, VolTarget size

It is a reading, not a forecast, and never investment advice.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from benchmark import DATA_DIR  # noqa: E402

SWING = 3  # a swing low/high is the lowest/highest close of the 3 days on each side


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def load(pair: str, timeframe: str, data_dir: Path = DATA_DIR) -> pd.DataFrame:
    path = data_dir / f"{pair.replace('/', '_')}-{timeframe}.feather"
    if not path.exists():
        raise SystemExit(f"{path.name} not found: run  ft.py chart --pair {pair}  (it downloads first)")
    return pd.read_feather(path).set_index("date")


def swings(close: pd.Series, k: int = SWING) -> tuple[list[float], list[float]]:
    """Daily closes that are the lowest (supports) / highest (resistances) of a 2k+1 day window."""
    lows, highs = [], []
    for i in range(k, len(close) - k):
        window = close.iloc[i - k : i + k + 1]
        if close.iloc[i] == window.min():
            lows.append(float(close.iloc[i]))
        if close.iloc[i] == window.max():
            highs.append(float(close.iloc[i]))
    return lows, highs


def daily_reading(d: pd.DataFrame) -> dict:
    c = d["close"]
    last = float(c.iloc[-1])
    out = {"date": str(d.index[-1].date()), "close": last}
    for n in (20, 50, 200):
        e = float(ema(c, n).iloc[-1])
        out[f"ema{n}"] = e
        out[f"vs_ema{n}"] = last / e - 1
    for n in (7, 30, 90):
        out[f"ret{n}"] = last / float(c.iloc[-1 - n]) - 1 if len(c) > n else float("nan")
    tail = c.iloc[-60:]
    out["high60"], out["low60"] = float(tail.max()), float(tail.min())
    lows, highs = swings(tail)
    out["support"] = max((x for x in lows if x < last), default=None)
    out["resistance"] = min((x for x in highs if x > last), default=None)
    out["vol30"] = float(np.log(c).diff().iloc[-30:].std() * np.sqrt(365))
    qv = d["close"] * d["volume"]
    out["volume_ratio"] = float(qv.iloc[-30:].mean() / qv.iloc[-90:].mean()) if len(qv) >= 90 else float("nan")
    return out


def bot_view(h: pd.DataFrame, target_vol: float = 0.60) -> dict:
    """TrendEma / TrendEmaVolTarget on 1h candles, on the last closed candle."""
    c = h["close"]
    fast, slow, trend = ema(c, 20), ema(c, 50), ema(c, 200)
    up = bool(fast.iloc[-1] > slow.iloc[-1])
    above = bool(c.iloc[-1] > trend.iloc[-1])
    crossed = bool(up and fast.iloc[-2] <= slow.iloc[-2])
    vol = float(np.log(c).diff().iloc[-24 * 30 :].std() * np.sqrt(24 * 365))
    scale = min(1.0, target_vol / vol) if vol > 0 else 1.0
    return {"short_up": up, "above_trend": above, "entry_now": crossed and above,
            "vol1h": vol, "size_scale": scale, "candle": str(h.index[-1])}  # fmt: skip


def render(pair: str, r: dict, b: dict) -> str:
    def pct(x):
        return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:+.1%}"

    def px(x, none="-"):
        if x is None:
            return none
        if abs(x) >= 1:
            return f"{x:,.2f}" if abs(x) >= 100 else f"{x:,.4f}"
        # tiny prices (PEPE 0.000005): plain decimals, 6 significant digits, no 5e-06
        return np.format_float_positional(x, precision=6, unique=False, fractional=False, trim="-")

    lines = [
        f"{pair}  daily, last closed candle {r['date']}  close {px(r['close'])}",
        f"  EMA20 {px(r['ema20'])} ({pct(r['vs_ema20'])})  EMA50 {px(r['ema50'])} ({pct(r['vs_ema50'])})"
        f"  EMA200 {px(r['ema200'])} ({pct(r['vs_ema200'])})   (+ = price above the line)",
        f"  return 7d {pct(r['ret7'])}  30d {pct(r['ret30'])}  90d {pct(r['ret90'])}",
        f"  60-day range {px(r['low60'])} .. {px(r['high60'])}   nearest support "
        f"{px(r['support'], 'none (price at its 60-day low)')}"
        f"  resistance {px(r['resistance'], 'none (price at its 60-day high)')}",
        f"  volatility 30d {r['vol30']:.0%}/year   volume last 30d vs 90d {r['volume_ratio']:.2f}x",
        f"Our bot works on 1-HOUR candles (a shorter view than the daily lines above), candle {b['candle']}:",
        f"  1h short trend {'UP' if b['short_up'] else 'DOWN'} (EMA20 vs EMA50), "
        f"{'above' if b['above_trend'] else 'below'} EMA200 -> entry signal now: {'YES' if b['entry_now'] else 'no'}",
        f"  VolTarget size: {b['size_scale']:.0%} of the normal stake (hourly volatility {b['vol1h']:.0%}/year)",
        "A reading of the past, not a forecast. Not investment advice.",
    ]
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--pair", required=True)
    p.add_argument("--data-dir", type=Path, default=DATA_DIR)
    a = p.parse_args()
    pair = a.pair.upper() if "/" in a.pair else f"{a.pair.upper()}/USDT"
    print(render(pair, daily_reading(load(pair, "1d", a.data_dir)), bot_view(load(pair, "1h", a.data_dir))))


if __name__ == "__main__":
    main()
