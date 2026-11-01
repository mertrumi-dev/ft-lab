"""One short table: every strategy's latest backtest on a slice, next to buy-and-hold.

Reads Freqtrade's saved results (user_data/backtest_results), so it runs inside
the Freqtrade container:

    python3 scripts/ft.py report --slice train
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import benchmark  # noqa: E402
import equity  # noqa: E402
from splits import SLICES  # noqa: E402
from universe import UNIVERSES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "user_data" / "backtest_results"
MIN_TRADES = 50
KILL_SWITCH_DRAWDOWN = 0.20  # same number as trend_ema.py; the bot stops buying at this drawdown


def result_fee(stats: dict) -> float | None:
    """Fee the backtest used, read from its first trade (None if it made no trades)."""
    trades = stats.get("trades") or []
    return trades[0].get("fee_open") if trades else None


def matches(stats: dict, timerange: str, pairs: list[str], fee: float) -> bool:
    """Same slice, same coin universe, same fee: only then are rows comparable."""
    run_fee = result_fee(stats)
    return (
        stats.get("timerange") == timerange
        and set(stats.get("pairlist", [])) <= set(pairs)
        and run_fee is not None
        and abs(run_fee - fee) < 1e-9
    )


def latest_stats_per_strategy(
    timerange: str, pairs: list[str], fee: float, results_dir: Path = RESULTS_DIR
) -> dict[str, dict]:
    """Newest result per strategy for this timerange, universe and fee."""
    from freqtrade.data.btanalysis import load_backtest_stats
    from freqtrade.data.btanalysis.bt_fileutils import _get_backtest_files

    found: dict[str, dict] = {}
    for path in _get_backtest_files(results_dir):  # newest first
        data = load_backtest_stats(path)
        for name, stats in data.get("strategy", {}).items():
            if name not in found and matches(stats, timerange, pairs, fee):
                found[name] = stats
    return found


def strategy_row(name: str, s: dict, hourly: dict | None = None) -> dict:
    """One table row. With `hourly` (open trades included) the drawdown and Calmar
    use the hourly measurement, the same way buy-and-hold is measured."""
    closed_mdd = s.get("max_drawdown_account", 0.0)
    mdd = hourly["max_drawdown_hourly"] if hourly else closed_mdd
    cagr = s.get("cagr", 0.0)
    return {
        "closed_drawdown": closed_mdd,
        "exposure": hourly["exposure"] if hourly else None,
        "name": name,
        "trades": s["total_trades"],
        "total_return": s["profit_total"],
        "cagr": cagr,
        "max_drawdown": mdd,
        "calmar": cagr / mdd if mdd > 0 else float("inf"),
        "win_rate": s["wins"] / s["total_trades"] if s["total_trades"] else 0.0,
        "profit_factor": s.get("profit_factor", 0.0),
        # date of the last closed trade: if it is long before the slice end, the bot stopped
        "last_trade": max((str(t["close_date"]) for t in s.get("trades", [])), default="")[:10],
    }


def verdict(row: dict, bh: dict, kill_switch_on: bool = True) -> str:
    """Our success rule from docs/risk-rules.md."""
    problems = []
    if row["trades"] < MIN_TRADES:
        problems.append(f"<{MIN_TRADES} trades")
    if row["calmar"] <= bh["calmar"]:
        problems.append("Calmar <= B&H")
    if row["max_drawdown"] >= bh["max_drawdown"] / 2:
        problems.append("DD >= half of B&H")
    result = "PASS" if not problems else "FAIL: " + ", ".join(problems)
    # the kill switch looks at CLOSED trades only, so use that drawdown here
    if row.get("closed_drawdown", row["max_drawdown"]) >= KILL_SWITCH_DRAWDOWN:
        result += (
            " [kill switch hit: stopped buying]"
            if kill_switch_on
            else " [DD >= 20%: a live bot would have stopped here]"
        )
    return result


def strategy_by_year(stats: dict) -> dict[int, dict]:
    """Per calendar year: trades, return and worst fall of the closed-trade balance.

    Balance starts at starting_balance and moves by each trade's profit when the
    trade closes (same view as Freqtrade's account drawdown).
    """
    trades = sorted(stats.get("trades", []), key=lambda t: str(t["close_date"]))
    balance = stats.get("starting_balance", 1000.0)
    years: dict[int, dict] = {}
    for t in trades:
        year = int(str(t["close_date"])[:4])
        y = years.setdefault(year, {"start": balance, "peak": balance, "dd": 0.0, "trades": 0})
        balance += t["profit_abs"]
        y["trades"] += 1
        y["peak"] = max(y["peak"], balance)
        y["dd"] = max(y["dd"], 1 - balance / y["peak"])
        y["end"] = balance
    return {
        year: {"trades": y["trades"], "return": y["end"] / y["start"] - 1, "max_drawdown": y["dd"]}
        for year, y in years.items()
    }


def format_years(stats: dict[str, dict], bh_years: dict[int, dict]) -> str:
    """One block per year: buy-and-hold vs every strategy, return and worst fall."""
    per_strategy = {name: strategy_by_year(st) for name, st in stats.items()}
    lines = []
    for year in sorted(bh_years):
        bh = bh_years[year]
        lines.append(f"\n{year:<18}{'Trd':>5}{'Return':>9}{'MaxDD':>8}")
        lines.append(f"  {'BUY & HOLD':<16}{'-':>5}{bh['return']:>+9.1%}{bh['max_drawdown']:>8.1%}")
        for name in sorted(per_strategy, key=lambda n: -per_strategy[n].get(year, {}).get("return", -9)):
            y = per_strategy[name].get(year)
            if y is None:
                lines.append(f"  {name:<16}{0:>5}{'no trades':>17}")
            else:
                lines.append(
                    f"  {name:<16}{y['trades']:>5}{y['return']:>+9.1%}{y['max_drawdown']:>8.1%}"
                )
    return "\n".join(lines)


def format_table(rows: list[dict], bh: dict, kill_switch_on: bool = True) -> str:
    head = (
        f"{'Strategy':<18}{'Trades':>7}{'Return':>9}{'CAGR':>8}{'MaxDD':>8}{'Calmar':>8}"
        f"{'Win%':>7}{'PF':>6}{'In coins':>9}{'Last trade':>12}  Verdict"
    )
    lines = [head, "-" * len(head)]
    lines.append(
        f"{'BUY & HOLD':<18}{'-':>7}{bh['total_return']:>+9.1%}{bh['cagr']:>+8.1%}"
        f"{bh['max_drawdown']:>8.1%}{bh['calmar']:>8.2f}{'-':>7}{'-':>6}{'100%':>9}{'-':>12}  (reference)"
    )
    for r in sorted(rows, key=lambda r: r["calmar"], reverse=True):
        lines.append(
            f"{r['name']:<18}{r['trades']:>7}{r['total_return']:>+9.1%}{r['cagr']:>+8.1%}"
            f"{r['max_drawdown']:>8.1%}{r['calmar']:>8.2f}{r['win_rate']:>7.0%}"
            f"{r['profit_factor']:>6.2f}"
            f"{(format(r['exposure'], '.0%') if r['exposure'] is not None else '-'):>9}"
            f"{r['last_trade']:>12}  {verdict(r, bh, kill_switch_on)}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--slice", choices=["train", "validation", "test"], required=True)
    parser.add_argument("--universe", choices=UNIVERSES, default="core")
    parser.add_argument("--fee", type=float, default=benchmark.DEFAULT_FEE)
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--by-year", action="store_true", help="add a year-by-year breakdown")
    parser.add_argument("--strategy", nargs="+", help="only these strategies")
    args = parser.parse_args()

    s = SLICES[args.slice]
    bh = benchmark.run(args.slice, "1h", args.fee, universe=args.universe)
    stats = latest_stats_per_strategy(
        s.timerange, benchmark.universe_pairs(args.universe), args.fee, args.results_dir
    )
    if not stats:
        raise SystemExit(
            f"No backtest results for --timerange {s.timerange}, universe {args.universe}, "
            f"fee {args.fee}. Run ft.py backtest first."
        )
    if args.strategy:
        stats = {name: st for name, st in stats.items() if name in args.strategy}
    rows = []
    for name, st in stats.items():
        curve = equity.build_curve(
            st.get("trades", []), bh["closes"], st.get("starting_balance", 1000.0), bh["index"]
        )
        rows.append(strategy_row(name, st, equity.summary(curve)))
    print(
        f"Slice: {args.slice}  --timerange {s.timerange}  universe {args.universe} "
        f"({len(bh['pairs'])} coins)  fee {args.fee:.2%}/side  start 1000 USDT"
    )
    if args.results_dir != RESULTS_DIR:
        print(f"Results from {args.results_dir.name} (research run, kill switch OFF)")
    if bh["skipped"]:
        print(f"No data (skipped): {', '.join(bh['skipped'])}")
    print("MaxDD and Calmar: measured every hour, open trades included (same as buy & hold).")
    print("In coins: average share of the money actually invested.")
    print(format_table(rows, bh, kill_switch_on=args.results_dir == RESULTS_DIR))
    if args.by_year:
        print("\nYear by year (strategy: closed trades only, so its MaxDD is optimistic)")
        print(format_years(stats, bh["years"]))


if __name__ == "__main__":
    main()
