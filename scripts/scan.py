"""Market scanner: what our bot's rule sees on many coins at once (research only).

    python3 scripts/ft.py scan                 # all 'pool' coins (about 60)
    python3 scripts/ft.py scan --universe core

For every coin with downloaded 1h candles, on the last closed candle:
  - trend state of the TrendEma rule (EMA20 vs EMA50, price vs EMA200)
  - entry signal right now (EMA20 crossed above EMA50 on this candle, price above EMA200)
  - VolTarget size: how much of the normal stake the bot would use (wild coin = smaller)
  - 30-day return and distance to EMA200

The bot itself trades only its 5 coins; this table only shows what the same rule
would think elsewhere. It is a reading of the past, never investment advice.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from benchmark import DATA_DIR  # noqa: E402
from chart import bot_view, ema  # noqa: E402
from universe import CORE_5, UNIVERSES  # noqa: E402

# coins whose Binance ticker today is not the coin the list was made for (thin, speculative markets)
CAVEATS = {
    "LUNA/USDT": "Terra 2.0, a new coin after the May 2022 crash",
    "FTT/USDT": "FTX token after the exchange went bankrupt (Nov 2022)",
}

# state labels, best first: the table is sorted by this order
STATES = ["ENTRY NOW", "in trend", "above EMA200, short trend down", "below EMA200"]


def scan_one(h: pd.DataFrame) -> dict:
    """One coin's row from its 1h candles (index = date, needs a 'close' column)."""
    b = bot_view(h)
    c = h["close"]
    last = float(c.iloc[-1])
    if b["entry_now"]:
        state = STATES[0]
    elif b["above_trend"] and b["short_up"]:
        state = STATES[1]
    elif b["above_trend"]:
        state = STATES[2]
    else:
        state = STATES[3]
    month_ago = c.index[-1] - pd.Timedelta(days=30)
    past = c[c.index <= month_ago]
    return {
        "state": state,
        "vs_ema200": last / float(ema(c, 200).iloc[-1]) - 1,
        "ret30": last / float(past.iloc[-1]) - 1 if len(past) else float("nan"),
        "size": b["size_scale"],
        "candle": b["candle"],
    }


def scan(pairs: list[str], data_dir: Path = DATA_DIR, min_candles: int = 24 * 30) -> tuple[pd.DataFrame, list[str]]:
    """Rows for every pair with enough 1h data, and the list of pairs skipped."""
    rows, skipped = [], []
    for pair in pairs:
        path = data_dir / f"{pair.replace('/', '_')}-1h.feather"
        if not path.exists():
            skipped.append(pair)
            continue
        h = pd.read_feather(path).set_index("date")
        if len(h) < min_candles:
            skipped.append(pair)
            continue
        rows.append({"pair": pair, **scan_one(h)})
    df = pd.DataFrame(rows)
    if not df.empty:
        df["order"] = df["state"].map(STATES.index)
        df = df.sort_values(["order", "vs_ema200"], ascending=[True, False]).drop(columns="order")
    return df.reset_index(drop=True), skipped


def render(df: pd.DataFrame, skipped: list[str]) -> str:
    if df.empty:
        return "no coins with 1h data"
    lines = [f"{'pair':<12} {'state':<32} {'vs EMA200':>9} {'30d':>8} {'size':>5}"]
    for r in df.itertuples():
        mark = " *" if r.pair in CORE_5 else (" !" if r.pair in CAVEATS else "")
        lines.append(f"{r.pair:<12} {r.state:<32} {r.vs_ema200:>+9.1%} {r.ret30:>+8.1%} {r.size:>5.0%}{mark}")
    counts = df["state"].value_counts()
    lines.append("")
    lines.append(f"{len(df)} coins, last candle {df['candle'].max()}: " + ", ".join(f"{s}: {counts.get(s, 0)}" for s in STATES))
    above = (df["vs_ema200"] > 0).mean()
    lines.append(f"market breadth: {above:.0%} of coins above their 1h EMA200")
    if skipped:
        lines.append(f"skipped (no or too little data): {', '.join(skipped)}")
    lines.append("* = one of the bot's 5 coins. size = VolTarget share of the normal stake.")
    for pair, why in CAVEATS.items():
        if pair in set(df["pair"]):
            lines.append(f"! {pair}: {why}; read with care")
    lines.append("A reading of the past, not a forecast. Not investment advice.")
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--universe", choices=[u for u in UNIVERSES if UNIVERSES[u]] + ["core"], default="pool")
    p.add_argument("--data-dir", type=Path, default=DATA_DIR)
    a = p.parse_args()
    pairs = UNIVERSES[a.universe] or CORE_5
    print(render(*scan(pairs, a.data_dir)))


if __name__ == "__main__":
    main()
