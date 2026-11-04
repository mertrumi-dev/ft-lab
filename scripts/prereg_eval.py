"""Measure one fresh-only row on its own window [start, judge) (read-only; `ft.py prereg-judge` calls it).

Prints a line "prereg_result: {json}" with the candidate's and VolTarget's Calmar, max drawdown
and trades, measured like `ft.py bots` (hourly equity, open trades marked to market) over the
core coins. The verdict itself is applied on the host by scripts/prereg.py (judge_row), so the
rule lives in one place and the result is written to docs/fresh/prereg-results.csv there.
Also a block-bootstrap p-value (bootstrap_p): information only, it never changes the verdict.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

FEE = 0.0015
BOOT_RUNS = 2000
BOOT_BLOCK = 7  # days, like scripts/expected.py: calm and wild weeks stay together
BOOT_SEED = 7


def _calmar_and_fall(returns, days_per_year: float = 365.25) -> tuple[float, float]:
    import numpy as np

    curve = np.cumprod(1 + returns)
    fall = float((1 - curve / np.maximum.accumulate(curve)).max())
    cagr = float(curve[-1]) ** (days_per_year / len(returns)) - 1
    return cagr / max(fall, 1e-6), fall


def bootstrap_p(cand_daily, base_daily, runs: int = BOOT_RUNS, block: int = BOOT_BLOCK, seed: int = BOOT_SEED) -> float | None:
    """One-sided p: how often does the candidate NOT beat the baseline when the same days are redrawn
    in blocks? "Beat" is the locked rule (prereg.judge_row): Calmar higher AND max drawdown not higher.
    Calmar alone would mislead: below zero a deeper fall makes it LESS negative (-97%/80% = -1.2 looks
    better than -60%/25% = -2.4). Both curves are redrawn together (same days), so market luck hits
    both alike. Low = the lead is steady across the window; high = a few days made it. None if too
    little data."""
    import numpy as np

    c, b = np.asarray(cand_daily, dtype=float), np.asarray(base_daily, dtype=float)
    n = len(c)
    if n != len(b) or n < 2 * block:
        return None
    rng = np.random.default_rng(seed)
    not_better = 0
    for _ in range(runs):
        starts = rng.integers(0, n - block + 1, size=n // block + 1)
        idx = np.concatenate([np.arange(s, s + block) for s in starts])[:n]
        cand_calmar, cand_fall = _calmar_and_fall(c[idx])
        base_calmar, base_fall = _calmar_and_fall(b[idx])
        not_better += not (cand_calmar > base_calmar and cand_fall <= base_fall)
    return (not_better + 1) / (runs + 1)


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
    p.add_argument("--confirm", action="store_true", help="second judgement of an ADAY row (the host records it separately)")
    a = p.parse_args()
    start, end = (pd.Timestamp(x, tz="UTC") for x in a.timerange.split("-"))
    pairs = benchmark.universe_pairs("core")
    closes = {}
    for pair in pairs:
        c = benchmark.load_closes(pair, "1h")
        closes[pair] = c[(c.index >= start) & (c.index < end)]
    index = pd.DatetimeIndex(sorted(set().union(*[set(c.index) for c in closes.values()])))
    stats = report.latest_stats_per_strategy(a.timerange, pairs, FEE, report.RESULTS_DIR)  # kill switch ON, as live
    out, curves = {}, {}
    for name in (a.strategy, a.baseline):
        st = stats.get(name)
        if not st:
            raise SystemExit(f"no backtest result for {name} on {a.timerange}")
        eq = build_curve(st.get("trades", []), closes, st.get("starting_balance", 1000.0), index)["equity"]
        out[name] = {**benchmark.summarize(eq), "trades": st["total_trades"]}
        curves[name] = eq.resample("1D").last().pct_change().dropna()
    p_value = bootstrap_p(curves[a.strategy].to_numpy(), curves[a.baseline].to_numpy())
    print("prereg_result: " + json.dumps({"candidate": out[a.strategy], "baseline": out[a.baseline], "boot_p": p_value}))


if __name__ == "__main__":
    main()
