"""Trade analysis: where does a strategy earn and where does it lose?

Reads the latest backtest result (no new backtest, no new trial) and splits the
trades by exit reason, by coin, by holding time and by year. The goal is to
find ONE weak spot to work on, instead of guessing.

    python3 scripts/ft.py analyze --slice train --no-kill-switch --strategy TrendEma
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import report  # noqa: E402
from benchmark import universe_pairs  # noqa: E402
from splits import SLICES  # noqa: E402
from universe import UNIVERSES  # noqa: E402

HOLD_BUCKETS = [0, 6, 24, 72, 168, 336, 10_000]  # hours: <6h, <1d, <3d, <1w, <2w, longer
HOLD_LABELS = ["<6h", "6h-1d", "1-3d", "3-7d", "1-2w", ">2w"]


def trades_frame(trades: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(trades)
    df["open_date"] = pd.to_datetime(df["open_date"], utc=True)
    df["close_date"] = pd.to_datetime(df["close_date"], utc=True)
    df["hours"] = (df["close_date"] - df["open_date"]).dt.total_seconds() / 3600
    df["hold"] = pd.cut(df["hours"], HOLD_BUCKETS, labels=HOLD_LABELS, right=False)
    df["year"] = df["close_date"].dt.year
    return df


def group_table(df: pd.DataFrame, by: str) -> pd.DataFrame:
    """Count, win rate, average and total profit (USDT and % of trade) per group."""
    g = df.groupby(by, observed=True)
    out = pd.DataFrame({
        "trades": g.size(),
        "win%": g["profit_abs"].apply(lambda p: (p > 0).mean() * 100),
        "avg%": g["profit_ratio"].mean() * 100,
        "total_usdt": g["profit_abs"].sum(),
        "avg_hours": g["hours"].mean(),
    })  # fmt: skip
    return out.sort_values("total_usdt")


def best_and_worst(df: pd.DataFrame, n: int = 5) -> tuple[pd.DataFrame, pd.DataFrame]:
    cols = ["pair", "open_date", "hours", "profit_ratio", "exit_reason"]
    ordered = df.sort_values("profit_ratio")
    return ordered.head(n)[cols], ordered.tail(n)[cols]


def concentration(df: pd.DataFrame, top: float = 0.10) -> float:
    """Share of the total profit made by the best `top` share of trades (0.1 = best 10%)."""
    total = df["profit_abs"].sum()
    k = max(1, int(len(df) * top))
    return float(df["profit_abs"].nlargest(k).sum() / total) if total else float("nan")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--slice", choices=["train"], required=True)  # analysis guides development: train only
    parser.add_argument("--strategy", nargs="+", required=True)
    parser.add_argument("--universe", choices=UNIVERSES, default="core")
    parser.add_argument("--fee", type=float, default=0.0015)
    parser.add_argument("--results-dir", type=Path, default=report.RESULTS_DIR)
    args = parser.parse_args()

    s = SLICES[args.slice]
    stats = report.latest_stats_per_strategy(s.timerange, universe_pairs(args.universe), args.fee, args.results_dir)
    pd.set_option("display.width", 140)
    pd.set_option("display.float_format", lambda v: f"{v:,.2f}")
    for name in args.strategy:
        st = stats.get(name)
        if not st or not st.get("trades"):
            print(f"{name}: no result for --timerange {s.timerange}, universe {args.universe}")
            continue
        df = trades_frame(st["trades"])
        print(f"=== {name}  --timerange {s.timerange}  universe {args.universe}  {len(df)} trades ===")
        for by in ("exit_reason", "pair", "hold", "year"):
            print(f"\n-- by {by} --")
            print(group_table(df, by).to_string())
        worst, best = best_and_worst(df)
        print("\n-- 5 worst trades --")
        print(worst.to_string(index=False))
        print("\n-- 5 best trades --")
        print(best.to_string(index=False))
        print(f"\nBest 10% of trades made {concentration(df):.0%} of the total profit.\n")


if __name__ == "__main__":
    main()
