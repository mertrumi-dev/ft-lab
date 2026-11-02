"""Which entries of the base rule did a filter NOT take? (read-only, existing backtest exports)

    python3 scripts/ft.py removed --strategy X [--base TrendEmaVolTarget] --slice train [--universe core]

For each removed entry (same pair + same open time in the base, missing in X): its P/L, the year,
the largest rise in the 7 days after entry (was it a real trend start?) and the 30-day volatility at
entry. Printed by year, because a filter can be good on average and still cut the best years
(docs/research/15-early-kirici.md). It never runs a backtest: a missing export is reported.
Helps understanding; it is not a verdict (that is scripts/criterion.py).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

BIG_RISE = 0.15  # "a real trend start": +15% within 7 days of the entry
WINDOW_7D = 24 * 7
VOL_WINDOW = 24 * 30
NO_KILL_DIR = Path("/freqtrade/user_data/backtest_results/no_kill_switch")


def entry_key(trade: dict) -> tuple[str, str]:
    return trade["pair"], str(trade["open_date"])[:16]


def removed_and_added(base: list[dict], cand: list[dict]) -> tuple[list[dict], list[dict]]:
    """Base entries the candidate did not take, and candidate entries the base did not take."""
    bk, ck = {entry_key(t) for t in base}, {entry_key(t) for t in cand}
    return [t for t in base if entry_key(t) not in ck], [t for t in cand if entry_key(t) not in bk]


def by_year(rows: list[dict]) -> list[dict]:
    """rows: {"year", "pl", "pr", "up7", "vol30"} -> one summary per year, oldest first."""
    out = []
    for y in sorted({r["year"] for r in rows}):
        sel = [r for r in rows if r["year"] == y]
        ups = [r["up7"] for r in sel if r["up7"] == r["up7"]]  # skip NaN
        vols = sorted(r["vol30"] for r in sel if r["vol30"] == r["vol30"])
        out.append({"year": y, "n": len(sel), "pl": sum(r["pl"] for r in sel),
                    "win": sum(r["pr"] > 0 for r in sel) / len(sel),
                    "big": (sum(u >= BIG_RISE for u in ups) / len(ups)) if ups else None,
                    "vol": vols[len(vols) // 2] if vols else None})  # fmt: skip
    return out


def render(title: str, base_pl: float, rows: list[dict], added_pl: float, n_base: int, n_added: int) -> str:
    total = sum(r["pl"] for r in rows)
    share = f"{total / base_pl:+.0%} of the base profit" if base_pl > 0 else "base profit <= 0"
    lines = [f"Removed entries: {title}",
             f"  removed {len(rows)} of {n_base} base entries, their P/L {total:+.1f} USDT ({share}); "
             f"added {n_added} new entries, their P/L {added_pl:+.1f}",
             f"  {'year':<6}{'trades':>7}{'P/L':>9}{'win':>6}{'rise>=15% in 7d':>17}{'vol30 med':>11}"]  # fmt: skip
    for y in by_year(rows):
        big = "-" if y["big"] is None else f"{y['big']:.0%}"
        vol = "-" if y["vol"] is None else f"{y['vol']:.0%}"
        lines.append(f"  {y['year']:<6}{y['n']:>7}{y['pl']:>+9.1f}{y['win']:>6.0%}{big:>17}{vol:>11}")
    lines.append("  Read: positive P/L in a year = the filter cut winners that year (often trend starts).")
    return "\n".join(lines)


def main() -> int:  # pragma: no cover - reads backtest results inside the container
    import numpy as np
    import pandas as pd

    import benchmark
    import report
    from splits import SLICES

    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--strategy", required=True)
    p.add_argument("--base", default="TrendEmaVolTarget")
    p.add_argument("--slice", required=True)
    p.add_argument("--universe", default="core")
    p.add_argument("--results-dir", type=Path, default=NO_KILL_DIR)
    a = p.parse_args()
    s = SLICES[a.slice]
    stats = report.latest_stats_per_strategy(s.timerange, benchmark.universe_pairs(a.universe), 0.0015, a.results_dir)
    missing = [n for n in (a.base, a.strategy) if n not in stats]
    if missing:
        print(f"removed: no backtest export for {', '.join(missing)} on {a.slice}/{a.universe} ({s.timerange}); "
              "backtest first (this tool never runs one)")  # fmt: skip
        return 0
    base, cand = stats[a.base]["trades"], stats[a.strategy]["trades"]
    gone, added = removed_and_added(base, cand)
    closes: dict = {}
    rows = []
    for t in gone:
        if t["pair"] not in closes:
            closes[t["pair"]] = benchmark.load_closes(t["pair"], "1h")
        c = closes[t["pair"]]
        ts = pd.Timestamp(t["open_date"])
        i = c.index.searchsorted(ts)
        px = c.iloc[i] if i < len(c) else np.nan
        fut = c.iloc[i:i + WINDOW_7D]
        past = np.log(c.iloc[max(0, i - VOL_WINDOW):i]).diff()
        rows.append({"year": ts.year, "pl": t["profit_abs"], "pr": t["profit_ratio"],
                     "up7": float(fut.max() / px - 1) if len(fut) else float("nan"),
                     "vol30": float(past.std() * np.sqrt(24 * 365)) if len(past) > 100 else float("nan")})  # fmt: skip
    print(render(f"{a.strategy} vs {a.base}, {a.slice}/{a.universe} ({s.timerange})",
                 sum(t["profit_abs"] for t in base), rows, sum(t["profit_abs"] for t in added), len(base), len(added)))  # fmt: skip
    return 0


if __name__ == "__main__":
    sys.exit(main())
