"""Strategy results over the FULL slice window (read-only; reads existing backtest results).

    python3 scripts/ft.py judge-eval --slice judge21 --universe judge_old --no-kill-switch --strategy A B C

`ft.py bots` puts every row on the window where ALL coins have data (it starts at the last
listing), which for a group with late listings shortens the window a lot. This tool keeps the
pre-registered window: each coin trades from its own first candle, the hourly equity curve
(open trades marked to market, like report.py) runs over the whole slice, and Calmar = CAGR /
hourly max drawdown. Also: fees paid and how many trades used a partial exit (order tag).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

FEE = 0.0015


def main() -> None:  # pragma: no cover - reads backtest results inside the container
    import pandas as pd

    import benchmark
    import report
    from equity import build_curve, max_drawdown
    from splits import SLICES

    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--slice", required=True)
    p.add_argument("--universe", required=True)
    p.add_argument("--results-dir", type=Path, default=report.RESULTS_DIR)
    p.add_argument("--strategy", nargs="+", required=True)
    a = p.parse_args()
    s = SLICES[a.slice]
    pairs = benchmark.universe_pairs(a.universe)
    closes = {}
    for pair in pairs:
        try:
            c = benchmark.load_closes(pair, "1h")
        except FileNotFoundError:
            continue
        closes[pair] = c[(c.index >= pd.Timestamp(s.start, tz="UTC")) & (c.index < pd.Timestamp(s.end, tz="UTC"))]
    index = pd.DatetimeIndex(sorted(set().union(*[set(c.index) for c in closes.values()])))
    stats = report.latest_stats_per_strategy(s.timerange, pairs, FEE, a.results_dir)
    years = (index[-1] - index[0]).days / 365.25
    print(f"Full-window results {a.slice} ({s.timerange}), {a.universe}: {len(closes)} coins with data, {index[0]:%Y-%m-%d} -> {index[-1]:%Y-%m-%d}")
    print(f"{'Strategy':<30}{'Trades':>7}{'Return':>10}{'CAGR':>9}{'MaxDD':>8}{'Calmar':>8}{'Fees':>9}{'PartialX':>9}")
    for name in a.strategy:
        st = stats.get(name)
        if not st:
            print(f"{name:<30} (no result)")
            continue
        tr = st["trades"]
        eq = build_curve(tr, closes, st.get("starting_balance", 1000.0), index)["equity"]
        total = float(eq.iloc[-1] / eq.iloc[0] - 1)
        cagr = (1 + total) ** (1 / years) - 1 if years > 0 else 0.0
        mdd = max_drawdown(eq)
        fees = sum(t["stake_amount"] * FEE + t["amount"] * t["close_rate"] * FEE for t in tr)
        partial = sum(sum(1 for o in t.get("orders", []) if o.get("ft_order_side") == "sell") > 1 for t in tr)
        print(f"{name:<30}{len(tr):>7}{total:>+10.1%}{cagr:>+9.1%}{mdd:>8.1%}{(cagr / mdd if mdd > 0 else float('inf')):>8.2f}"
              f"{fees:>9.1f}{partial:>9}")  # fmt: skip


if __name__ == "__main__":
    main()
