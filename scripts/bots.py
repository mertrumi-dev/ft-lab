"""Famous bot types vs our rule, on the same coins, slice and fee.

Prints one table: buy-and-hold, weekly DCA (the "savings plan" bot),
a Pionex/Binance-style grid bot, a 3Commas-style DCA bot, and every
Freqtrade strategy you name (e.g. TrendEma and the NFI benchmark), whose
latest backtest results are read from disk like report.py does.

    python3 scripts/ft.py bots --slice train --no-kill-switch --strategy TrendEma NostalgiaForInfinityX8

The simulated bots (grid, DCA bot) use the same 1h candles and the same fee
(0.15% per side) as our backtests. Drawdown is hourly for all rows.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dcabot  # noqa: E402
import grid  # noqa: E402
import report  # noqa: E402
from benchmark import DATA_DIR, DEFAULT_FEE, by_year, dca_equity, summarize, universe_pairs  # noqa: E402
from benchmark import run as benchmark_run  # noqa: E402
from equity import build_curve  # noqa: E402
from splits import SLICES  # noqa: E402
from universe import UNIVERSES  # noqa: E402


def simulate_bot(sim, slice_name: str, universe: str, fee: float, data_dir: Path = DATA_DIR) -> dict:
    """Run a per-coin simulator on every coin with an equal share of the money."""
    pairs = universe_pairs(universe)
    curves, count = {}, 0
    for pair in pairs:
        try:
            candles = grid.load_candles(pair, slice_name, data_dir)
        except FileNotFoundError:
            continue
        curve, n = sim(candles, 1.0, fee=fee)
        curves[pair], count = curve, count + n
    equity = pd.DataFrame(curves).dropna().mean(axis=1)  # each coin started at 1.0
    out = summarize(equity)
    out.update(trades=count, years=by_year(equity), exposure=None)
    return out


def row(name: str, r: dict) -> str:
    trades = "-" if r.get("trades") is None else str(r["trades"])
    warn = "  <50 trades" if isinstance(r.get("trades"), int) and r["trades"] < report.MIN_TRADES else ""
    return (f"{name:<24}{trades:>7}{r['total_return']:>+10.1%}{r['cagr']:>+9.1%}"
            f"{r['max_drawdown']:>8.1%}{r['calmar']:>8.2f}{warn}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--slice", choices=["train", "validation"], required=True)
    parser.add_argument("--universe", choices=UNIVERSES, default="core")
    parser.add_argument("--fee", type=float, default=DEFAULT_FEE)
    parser.add_argument("--strategy", nargs="*", default=["TrendEma"])
    parser.add_argument("--results-dir", type=Path, default=report.RESULTS_DIR)
    args = parser.parse_args()

    s = SLICES[args.slice]
    bh = benchmark_run(args.slice, "1h", args.fee, universe=args.universe)
    rows = [("Buy & hold", {**bh, "trades": None}),
            ("Weekly DCA (savings)", {**summarize(dca_equity(bh["closes"], args.fee)), "trades": None}),
            ("Grid bot (Pionex-style)", simulate_bot(
                lambda c, cash, fee: grid.simulate_pair(c, cash, fee=fee), args.slice, args.universe, args.fee)),
            ("DCA bot (3Commas-style)", simulate_bot(
                dcabot.simulate_pair, args.slice, args.universe, args.fee))]  # fmt: skip

    stats = report.latest_stats_per_strategy(
        s.timerange, universe_pairs(args.universe), args.fee, args.results_dir)
    for name in args.strategy:
        st = stats.get(name)
        if not st:
            print(f"(no backtest result for {name} on this slice/universe/fee: backtest it first)")
            continue
        curve = build_curve(st.get("trades", []), bh["closes"], st.get("starting_balance", 1000.0), bh["index"])
        r = summarize(curve["equity"])
        r["trades"] = st["total_trades"]
        rows.append((name, r))

    print(f"Famous bot types vs our rule, --timerange {s.timerange}, universe {args.universe}, "
          f"fee {args.fee:.2%}/side, hourly drawdown")
    head = f"{'Bot':<24}{'Trades':>7}{'Return':>10}{'CAGR':>9}{'MaxDD':>8}{'Calmar':>8}"
    print(head)
    print("-" * len(head))
    for name, r in rows:
        print(row(name, r))
    print("Trades: grid = finished buy-sell round trips, DCA bot = finished deals.")


if __name__ == "__main__":
    main()
