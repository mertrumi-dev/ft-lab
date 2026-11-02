"""Measure one fresh-only row on its own window [start, judge) (read-only; `ft.py prereg-judge` calls it).

Prints a line "prereg_result: {json}" with the candidate's and VolTarget's Calmar, max drawdown
and trades, measured like `ft.py bots` (hourly equity, open trades marked to market) over the
core coins. The verdict itself is applied on the host by scripts/prereg.py (judge_row), so the
rule lives in one place and the result is written to docs/fresh/prereg-results.csv there.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

FEE = 0.0015


def main() -> None:  # pragma: no cover - reads backtest results inside the container
    import pandas as pd

    import benchmark
    import report
    from equity import build_curve

    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--strategy", required=True)
    p.add_argument("--baseline", default="TrendEmaVolTarget")
    p.add_argument("--timerange", required=True)
    p.add_argument("--id", help="the row id (the host records the result under it)")
    a = p.parse_args()
    start, end = (pd.Timestamp(x, tz="UTC") for x in a.timerange.split("-"))
    pairs = benchmark.universe_pairs("core")
    closes = {}
    for pair in pairs:
        c = benchmark.load_closes(pair, "1h")
        closes[pair] = c[(c.index >= start) & (c.index < end)]
    index = pd.DatetimeIndex(sorted(set().union(*[set(c.index) for c in closes.values()])))
    stats = report.latest_stats_per_strategy(a.timerange, pairs, FEE, report.RESULTS_DIR)  # kill switch ON, as live
    out = {}
    for name in (a.strategy, a.baseline):
        st = stats.get(name)
        if not st:
            raise SystemExit(f"no backtest result for {name} on {a.timerange}")
        eq = build_curve(st.get("trades", []), closes, st.get("starting_balance", 1000.0), index)["equity"]
        out[name] = {**benchmark.summarize(eq), "trades": st["total_trades"]}
    print("prereg_result: " + json.dumps({"candidate": out[a.strategy], "baseline": out[a.baseline]}))


if __name__ == "__main__":
    main()
