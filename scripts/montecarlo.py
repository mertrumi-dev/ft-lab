"""Monte Carlo: "how bad could it have been with a bit less luck?"

A backtest gives ONE order of trades. The same trades in another order can
give a much deeper drawdown. We take each trade's result as a share of the
account at that time, draw the trades again at random (with replacement,
"bootstrap") 2000 times, and look at the spread of outcomes.

    python3 scripts/ft.py montecarlo --slice train --strategy TrendEma

Reads Freqtrade results, so it runs inside the container (like report.py).
"""

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import report  # noqa: E402
from benchmark import universe_pairs  # noqa: E402
from splits import SLICES  # noqa: E402
from universe import UNIVERSES  # noqa: E402

RUNS = 2000
SEED = 42  # fixed, so the same input always gives the same answer


def trade_returns(trades: list[dict], start_balance: float) -> np.ndarray:
    """Each trade's profit as a share of the account balance just before it closed."""
    balance, out = start_balance, []
    for t in sorted(trades, key=lambda t: str(t["close_date"])):
        out.append(t["profit_abs"] / balance)
        balance += t["profit_abs"]
    return np.array(out)


def simulate(returns: np.ndarray, years: float, runs: int = RUNS, seed: int = SEED) -> dict:
    """Bootstrap the trade list; percentiles of max drawdown and yearly growth."""
    rng = np.random.default_rng(seed)
    picks = rng.choice(returns, size=(runs, len(returns)), replace=True)
    equity = np.cumprod(1 + picks, axis=1)
    equity = np.hstack([np.ones((runs, 1)), equity])
    dd = (1 - equity / np.maximum.accumulate(equity, axis=1)).max(axis=1)
    cagr = equity[:, -1] ** (1 / years) - 1
    pct = lambda a, q: float(np.percentile(a, q))  # noqa: E731
    return {
        "dd_median": pct(dd, 50), "dd_p95": pct(dd, 95), "dd_worst": float(dd.max()),
        "cagr_p5": pct(cagr, 5), "cagr_median": pct(cagr, 50),
        "loss_chance": float((equity[:, -1] < 1).mean()),
        "dd_over_20": float((dd >= 0.20).mean()),
    }  # fmt: skip


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--slice", choices=["train", "validation"], required=True)
    parser.add_argument("--strategy", nargs="+", required=True)
    parser.add_argument("--universe", choices=UNIVERSES, default="core")
    parser.add_argument("--fee", type=float, default=0.0015)
    parser.add_argument("--results-dir", type=Path, default=report.RESULTS_DIR)
    args = parser.parse_args()

    s = SLICES[args.slice]
    years = (s.end - s.start).days / 365.25
    stats = report.latest_stats_per_strategy(
        s.timerange, universe_pairs(args.universe), args.fee, args.results_dir
    )
    print(f"Monte Carlo, {RUNS} reshuffles of the trade list, --timerange {s.timerange}, "
          f"universe {args.universe}. Drawdown here = closed trades only.")
    head = f"{'Strategy':<18}{'Trades':>7}{'DD med':>8}{'DD 95%':>8}{'DD worst':>9}{'CAGR 5%':>9}{'CAGR med':>9}{'P(loss)':>8}{'P(DD>=20%)':>11}"
    print(head)
    print("-" * len(head))
    for name in args.strategy:
        st = stats.get(name)
        if not st:
            print(f"{name:<18} no result for this slice/universe/fee")
            continue
        r = simulate(trade_returns(st["trades"], st.get("starting_balance", 1000.0)), years)
        print(f"{name:<18}{st['total_trades']:>7}{r['dd_median']:>8.1%}{r['dd_p95']:>8.1%}"
              f"{r['dd_worst']:>9.1%}{r['cagr_p5']:>+9.1%}{r['cagr_median']:>+9.1%}"
              f"{r['loss_chance']:>8.1%}{r['dd_over_20']:>11.1%}")


if __name__ == "__main__":
    main()
