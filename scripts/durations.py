"""Trade duration vs P/L and fees, from EXISTING backtest results (read-only, runs no backtest).

    python3 scripts/ft.py durations --slice train --no-kill-switch --strategy TrendEmaVolTarget
    python3 scripts/ft.py durations --slice window24 --universe alt2024b --no-kill-switch --strategy A B

For each hold-time bucket: trades, win rate, P/L, fees paid (0.15% per side on the stake in and
the value out) and P/L before fees. It answers "where do the fees and losses come from?",
the question behind the minimum-hold-time trial (T106, MinHold24).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

FEE = 0.0015
BUCKETS = [(0, 6, "< 6 saat"), (6, 24, "6-24 saat"), (24, 72, "1-3 gün"), (72, 168, "3-7 gün"),
           (168, 336, "1-2 hafta"), (336, 10**9, "> 2 hafta")]  # fmt: skip


def hours(trade: dict) -> float:
    from datetime import datetime

    def ts(x):
        return datetime.fromisoformat(str(x).replace("Z", "+00:00"))

    return (ts(trade["close_date"]) - ts(trade["open_date"])).total_seconds() / 3600


def fees(trade: dict, fee: float = FEE) -> float:
    """Entry fee on the stake + exit fee on the value sold (both sides of every order)."""
    out = trade["amount"] * trade["close_rate"]
    return trade["stake_amount"] * fee + out * fee


def table(trades: list[dict]) -> list[dict]:
    rows = []
    for lo, hi, label in BUCKETS:
        sel = [t for t in trades if lo <= hours(t) < hi]
        pl = sum(t["profit_abs"] for t in sel)
        fe = sum(fees(t) for t in sel)
        rows.append({"bucket": label, "trades": len(sel), "win": (sum(t["profit_abs"] > 0 for t in sel) / len(sel)) if sel else None,
                     "pl": pl, "fees": fe, "before_fees": pl + fe})  # fmt: skip
    return rows


def render(name: str, rows: list[dict]) -> str:
    total = {k: sum(r[k] for r in rows) for k in ("trades", "pl", "fees", "before_fees")}
    lines = [f"### {name}", "", "| Tutma süresi | İşlem | Kazanan | K/Z USDT | Komisyon | Komisyonsuz K/Z |", "|---|---|---|---|---|---|"]
    for r in rows:
        win = "-" if r["win"] is None else f"%{r['win'] * 100:.0f}"
        lines.append(f"| {r['bucket']} | {r['trades']} | {win} | {r['pl']:+.1f} | {r['fees']:.1f} | {r['before_fees']:+.1f} |")
    lines.append(f"| **Toplam** | {total['trades']} | | {total['pl']:+.1f} | {total['fees']:.1f} | {total['before_fees']:+.1f} |")
    return "\n".join(lines)


def main() -> None:  # pragma: no cover - reads backtest results inside the container
    import benchmark
    import report
    from splits import SLICES

    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--slice", required=True)
    p.add_argument("--universe", default="core")
    p.add_argument("--results-dir", type=Path, default=report.RESULTS_DIR)
    p.add_argument("--strategy", nargs="+", required=True)
    a = p.parse_args()
    stats = report.latest_stats_per_strategy(SLICES[a.slice].timerange, benchmark.universe_pairs(a.universe), FEE, a.results_dir)
    for name in a.strategy:
        st = stats.get(name)
        if not st:
            print(f"(no result for {name} on {a.slice}/{a.universe}: nothing to read)")
            continue
        print(render(f"{name}, {a.slice} {a.universe} ({SLICES[a.slice].timerange})", table(st["trades"])))
        print()


if __name__ == "__main__":
    main()
