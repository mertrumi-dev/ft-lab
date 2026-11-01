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
import rotation  # noqa: E402
from benchmark import DATA_DIR, DEFAULT_FEE, by_year, dca_equity, load_closes, summarize, universe_pairs, window_warning  # noqa: E402
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
    out.update(trades=count, years=by_year(equity), exposure=None, equity=equity)
    return out


def rotation_bot(
    slice_name: str, universe: str, fee: float, data_dir: Path = DATA_DIR, start: pd.Timestamp | None = None
) -> dict:
    """Our weekly momentum rotation (scripts/rotation.py) on the same coins.

    Scores need history from BEFORE the slice (30 days, BTC 100-day average),
    so the full files are read and only the slice's hours are traded.
    """
    s = SLICES[slice_name]
    full = {}
    for pair in universe_pairs(universe):
        try:
            full[pair] = load_closes(pair, "1h", data_dir)
        except FileNotFoundError:
            continue
    btc = rotation.daily_closes({"BTC": load_closes("BTC/USDT", "1h", data_dir)})["BTC"]
    weights = rotation.target_weights(rotation.daily_closes(full), btc)
    end = pd.Timestamp(s.end, tz="UTC")
    start = max(start, pd.Timestamp(s.start, tz="UTC")) if start is not None else pd.Timestamp(s.start, tz="UTC")
    hourly = pd.DataFrame(full).sort_index().ffill()
    hourly = hourly[(hourly.index >= start) & (hourly.index < end)]
    equity, orders = rotation.simulate(hourly, weights[(weights.index >= start - pd.Timedelta(days=1))], fee)
    return with_years(equity, orders)


def half_and_half(a: pd.Series, b: pd.Series) -> pd.Series:
    """Two separate accounts with half the money each, never rebalanced.

    Like running two bots side by side: each keeps its own profits and losses.
    Both curves are scaled to start at 0.5, then added hour by hour.
    """
    frame = pd.concat([a, b], axis=1).sort_index().ffill().dropna()
    return 0.5 * frame.iloc[:, 0] / frame.iloc[0, 0] + 0.5 * frame.iloc[:, 1] / frame.iloc[0, 1]


def with_years(equity: pd.Series, trades) -> dict:
    out = summarize(equity)
    out.update(trades=trades, years=by_year(equity), equity=equity)
    return out


def format_years(rows: list[tuple[str, dict]]) -> str:
    """Return / worst fall inside each calendar year, one line per bot."""
    years = sorted({y for _, r in rows for y in r.get("years", {})})
    head = f"{'Year by year':<24}" + "".join(f"{y:>16}" for y in years)
    lines = [head, "-" * len(head)]
    for name, r in rows:
        cells = []
        for y in years:
            v = r.get("years", {}).get(y)
            cells.append(f"{v['return']:>+8.1%} DD{v['max_drawdown']:>4.0%}" if v else f"{'-':>16}")
        lines.append(f"{name:<24}" + "".join(f"{c:>16}" for c in cells))
    return "\n".join(lines)


def row(name: str, r: dict) -> str:
    trades = "-" if r.get("trades") is None else str(r["trades"])
    warn = "  <50 trades" if isinstance(r.get("trades"), int) and r["trades"] < report.MIN_TRADES else ""
    return (f"{name:<24}{trades:>7}{r['total_return']:>+10.1%}{r['cagr']:>+9.1%}"
            f"{r['max_drawdown']:>8.1%}{r['calmar']:>8.2f}{warn}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--slice", choices=["train", "validation", "test", "fresh"], required=True)  # ft.py guards test
    parser.add_argument("--universe", choices=UNIVERSES, default="core")
    parser.add_argument("--fee", type=float, default=DEFAULT_FEE)
    parser.add_argument("--strategy", nargs="*", default=["TrendEma"])
    parser.add_argument("--results-dir", type=Path, default=report.RESULTS_DIR)
    args = parser.parse_args()

    s = SLICES[args.slice]
    bh = benchmark_run(args.slice, "1h", args.fee, universe=args.universe)
    rows = [("Buy & hold", {**bh, "trades": None}),
            ("Weekly DCA (savings)", with_years(dca_equity(bh["closes"], args.fee), None)),
            ("Grid bot (Pionex-style)", simulate_bot(
                lambda c, cash, fee: grid.simulate_pair(c, cash, fee=fee), args.slice, args.universe, args.fee)),
            ("DCA bot (3Commas-style)", simulate_bot(
                dcabot.simulate_pair, args.slice, args.universe, args.fee)),
            ("Rotation (ours, weekly)", rotation_bot(args.slice, args.universe, args.fee, start=bh["index"][0]))]  # fmt: skip

    stats = report.latest_stats_per_strategy(
        s.timerange, universe_pairs(args.universe), args.fee, args.results_dir)
    for name in args.strategy:
        st = stats.get(name)
        if not st:
            print(f"(no backtest result for {name} on this slice/universe/fee: backtest it first)")
            continue
        curve = build_curve(st.get("trades", []), bh["closes"], st.get("starting_balance", 1000.0), bh["index"])
        r = with_years(curve["equity"], st["total_trades"])
        rows.append((name, r))
        if name == "TrendEma":
            # Combination idea (decided before seeing it): trend rule + grid bot, 50/50.
            # They earn in different markets (trends vs sideways), so together the
            # curve may be smoother. Counted as one trial in docs/journal.md.
            combo = with_years(half_and_half(curve["equity"], rows[2][1]["equity"]),
                               r["trades"] + rows[2][1]["trades"])  # fmt: skip
            rows.append(("TrendEma 50% + Grid 50%", combo))
        if name == "TrendEmaBtcRisingGap":
            # Portfolio idea (pre-registered 2026-11-01, research only, no tuning):
            # the DCA bot earns in up/sideways markets, the Gap rule protects in
            # down markets, so two separate half accounts may be steadier than either.
            dca = rows[3][1]
            combo = with_years(half_and_half(dca["equity"], curve["equity"]), r["trades"] + dca["trades"])
            rows.append(("DCA bot 50% + Gap 50%", combo))

    warn = window_warning(s.start, bh["index"])
    if warn:
        print(warn.split(" Return")[0] + " Every row below uses that same shorter window.")
    print(f"Famous bot types vs our rule, --timerange {s.timerange}, universe {args.universe}, "
          f"fee {args.fee:.2%}/side, hourly drawdown")
    head = f"{'Bot':<24}{'Trades':>7}{'Return':>10}{'CAGR':>9}{'MaxDD':>8}{'Calmar':>8}"
    print(head)
    print("-" * len(head))
    for name, r in rows:
        print(row(name, r))
    print("Trades: grid = finished buy-sell round trips, DCA bot = finished deals, rotation = orders.")
    print()
    print(format_years(rows))


if __name__ == "__main__":
    main()
