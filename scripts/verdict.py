"""Measure a trial from EXISTING backtest results and print the standard verdict (read-only).

    python3 scripts/ft.py verdict --strategy X [--baseline TrendEmaVolTarget] [--neighbours A B] [--robust]

Numbers are measured exactly like `ft.py bots` (hourly equity curve over the same window, open
trades marked to market, Calmar = CAGR / max drawdown). The rules live in scripts/criterion.py.
`ft.py trial` runs the backtests first and then this.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import criterion  # noqa: E402

FEE = 0.0015
STRESS_FEE = 0.003
NO_KILL_DIR = Path("/freqtrade/user_data/backtest_results/no_kill_switch")


def measure(strategies: list[str], slice_name: str, universe: str, fee: float, results_dir: Path) -> dict:  # pragma: no cover - container
    import benchmark
    import report
    from equity import build_curve
    from splits import SLICES

    bh = benchmark.run(slice_name, "1h", fee, universe=universe)
    stats = report.latest_stats_per_strategy(SLICES[slice_name].timerange, benchmark.universe_pairs(universe), fee, results_dir)
    out = {}
    for name in strategies:
        st = stats.get(name)
        if not st:
            continue
        curve = build_curve(st.get("trades", []), bh["closes"], st.get("starting_balance", 1000.0), bh["index"])
        out[name] = {**benchmark.summarize(curve["equity"]), "trades": st["total_trades"]}
    return out


def collect(names: list[str], cases, fee: float, results_dir: Path) -> dict:  # pragma: no cover - container
    """{strategy: {slice: numbers}} over the given cases."""
    per = {n: {} for n in names}
    for slice_name, universe in cases:
        for n, m in measure(names, slice_name, universe, fee, results_dir).items():
            per[n][slice_name] = m
    return per


def main() -> None:  # pragma: no cover - container
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--strategy", required=True)
    p.add_argument("--baseline", default="TrendEmaVolTarget")
    p.add_argument("--neighbours", nargs="*", default=[])
    p.add_argument("--robust", action="store_true", help="also read the plateau (neighbours) and fee x2")
    p.add_argument("--results-dir", type=Path, default=NO_KILL_DIR)
    a = p.parse_args()
    main_per = collect([a.strategy, a.baseline], criterion.CASES, FEE, a.results_dir)
    neighbours = cand_fee = base_fee = None
    if a.robust:
        neighbours = {n: v for n, v in collect(a.neighbours, criterion.NEIGHBOUR_CASES, FEE, a.results_dir).items()}
        fee_per = collect([a.strategy, a.baseline], criterion.FEE_CASES, STRESS_FEE, a.results_dir)
        cand_fee, base_fee = fee_per[a.strategy], fee_per[a.baseline]
    v = criterion.verdict(main_per[a.strategy], main_per[a.baseline], neighbours, cand_fee, base_fee)
    print(criterion.render(v, a.strategy, a.baseline))


if __name__ == "__main__":
    main()
