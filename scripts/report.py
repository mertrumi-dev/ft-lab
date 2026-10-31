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
from splits import SLICES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "user_data" / "backtest_results"
MIN_TRADES = 50


def latest_stats_per_strategy(timerange: str, results_dir: Path = RESULTS_DIR) -> dict[str, dict]:
    """Newest result per strategy for this exact timerange."""
    from freqtrade.data.btanalysis import load_backtest_stats
    from freqtrade.data.btanalysis.bt_fileutils import _get_backtest_files

    found: dict[str, dict] = {}
    for path in _get_backtest_files(results_dir):  # newest first
        data = load_backtest_stats(path)
        for name, stats in data.get("strategy", {}).items():
            if name not in found and stats.get("timerange") == timerange:
                found[name] = stats
    return found


def strategy_row(name: str, s: dict) -> dict:
    mdd = s.get("max_drawdown_account", 0.0)
    cagr = s.get("cagr", 0.0)
    return {
        "name": name,
        "trades": s["total_trades"],
        "total_return": s["profit_total"],
        "cagr": cagr,
        "max_drawdown": mdd,
        "calmar": cagr / mdd if mdd > 0 else float("inf"),
        "win_rate": s["wins"] / s["total_trades"] if s["total_trades"] else 0.0,
        "profit_factor": s.get("profit_factor", 0.0),
    }


def verdict(row: dict, bh: dict) -> str:
    """Our success rule from docs/risk-rules.md."""
    problems = []
    if row["trades"] < MIN_TRADES:
        problems.append(f"<{MIN_TRADES} trades")
    if row["calmar"] <= bh["calmar"]:
        problems.append("Calmar <= B&H")
    if row["max_drawdown"] >= bh["max_drawdown"] / 2:
        problems.append("DD >= half of B&H")
    return "PASS" if not problems else "FAIL: " + ", ".join(problems)


def format_table(rows: list[dict], bh: dict) -> str:
    head = f"{'Strategy':<18}{'Trades':>7}{'Return':>9}{'CAGR':>8}{'MaxDD':>8}{'Calmar':>8}{'Win%':>7}{'PF':>6}  Verdict"
    lines = [head, "-" * len(head)]
    lines.append(
        f"{'BUY & HOLD':<18}{'-':>7}{bh['total_return']:>+9.1%}{bh['cagr']:>+8.1%}"
        f"{bh['max_drawdown']:>8.1%}{bh['calmar']:>8.2f}{'-':>7}{'-':>6}  (reference)"
    )
    for r in sorted(rows, key=lambda r: r["calmar"], reverse=True):
        lines.append(
            f"{r['name']:<18}{r['trades']:>7}{r['total_return']:>+9.1%}{r['cagr']:>+8.1%}"
            f"{r['max_drawdown']:>8.1%}{r['calmar']:>8.2f}{r['win_rate']:>7.0%}"
            f"{r['profit_factor']:>6.2f}  {verdict(r, bh)}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--slice", choices=["train", "validation", "test"], required=True)
    args = parser.parse_args()

    s = SLICES[args.slice]
    bh = benchmark.run(args.slice, "1h", benchmark.DEFAULT_FEE)
    stats = latest_stats_per_strategy(s.timerange)
    if not stats:
        raise SystemExit(f"No backtest results for --timerange {s.timerange}. Run ft.py backtest first.")
    rows = [strategy_row(name, st) for name, st in stats.items()]
    print(f"Slice: {args.slice}  --timerange {s.timerange}  fee 0.15%/side  start 1000 USDT")
    print(format_table(rows, bh))


if __name__ == "__main__":
    main()
