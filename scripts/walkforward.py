"""Walk-forward: "does picking the best settings from the past help in the future?"

Inside the TRAIN slice only. We cut it into half-year windows. Before each
window we look back 12 months, pick the candidate (e.g. TrendEma and its 6
sensitivity neighbours) that did best there, and then use ONLY that candidate's
trades in the next window, which it has not been chosen on. Chaining those
"next windows" gives an honest, out-of-sample result for the habit "always use
whatever worked lately".

We compare it with simply keeping one fixed rule (TrendEma) the whole time.
If picking does not beat fixed, re-tuning the numbers adds nothing but risk.

    python3 scripts/ft.py walkforward --slice train --no-kill-switch

Uses existing backtest results, so no new backtest (and no new trial) is
needed. Each candidate's trade results are taken as a share of the account
(see montecarlo.trade_returns), so candidates with different balance paths
can be chained. Drawdown here = closed trades only.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import report  # noqa: E402
from benchmark import universe_pairs  # noqa: E402
from splits import SLICES  # noqa: E402
from universe import UNIVERSES  # noqa: E402

DEFAULT_CANDIDATES = [
    "TrendEma", "EmaFast15", "EmaFast25", "EmaSlow40", "EmaSlow60", "EmaTrend150", "EmaTrend250",
]  # fmt: skip
STEP_MONTHS = 6  # each out-of-sample window is half a year
LOOKBACK_MONTHS = 12  # choose on the 12 months before it


def trade_series(trades: list[dict], start_balance: float) -> pd.Series:
    """Each closed trade's result as a share of the account, indexed by close time."""
    balance, rows = start_balance, []
    for t in sorted(trades, key=lambda t: str(t["close_date"])):
        rows.append((pd.Timestamp(t["close_date"]), t["profit_abs"] / balance))
        balance += t["profit_abs"]
    if not rows:
        return pd.Series(dtype=float)
    idx, vals = zip(*rows)
    s = pd.Series(vals, index=pd.DatetimeIndex(idx))
    return s.tz_localize("UTC") if s.index.tz is None else s.tz_convert("UTC")


def windows(start: pd.Timestamp, end: pd.Timestamp, step_months: int = STEP_MONTHS) -> list[tuple]:
    """Consecutive [from, to) windows of `step_months`; the last one is cut at `end`."""
    out, cur = [], start
    while cur < end:
        nxt = min(cur + pd.DateOffset(months=step_months), end)
        out.append((cur, nxt))
        cur = nxt
    return out


def part(returns: pd.Series, start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    return returns[(returns.index >= start) & (returns.index < end)]


def growth(returns: pd.Series) -> float:
    """Total return of chained trades (0.10 = +10%)."""
    return float(np.prod(1 + returns.to_numpy()) - 1) if len(returns) else 0.0


def closed_drawdown(returns: pd.Series) -> float:
    """Worst fall from a peak of the chained-trade equity (closed trades only)."""
    if not len(returns):
        return 0.0
    equity = np.concatenate([[1.0], np.cumprod(1 + returns.to_numpy())])
    return float((1 - equity / np.maximum.accumulate(equity)).max())


def score(returns: pd.Series) -> float:
    """How we rank candidates on the lookback: return per unit of drawdown (Calmar-like).

    A floor of 1% on the drawdown keeps a lucky period with almost no fall
    from getting an infinite score.
    """
    return growth(returns) / max(closed_drawdown(returns), 0.01)


def walk_forward(
    candidates: dict[str, pd.Series],
    start: pd.Timestamp,
    end: pd.Timestamp,
    fixed: str,
    lookback_months: int = LOOKBACK_MONTHS,
    step_months: int = STEP_MONTHS,
) -> dict:
    """Pick on the lookback, trade the next window; also the fixed rule on the same windows."""
    first_oos = start + pd.DateOffset(months=lookback_months)
    rows, picked_parts, fixed_parts = [], [], []
    for w_start, w_end in windows(first_oos, end, step_months):
        look_from = w_start - pd.DateOffset(months=lookback_months)
        scores = {n: score(part(r, look_from, w_start)) for n, r in candidates.items()}
        chosen = max(scores, key=lambda n: (scores[n], n == fixed))  # tie -> keep the fixed rule
        oos = part(candidates[chosen], w_start, w_end)
        fix = part(candidates[fixed], w_start, w_end)
        picked_parts.append(oos)
        fixed_parts.append(fix)
        rows.append({
            "from": w_start, "to": w_end, "chosen": chosen,
            "chosen_return": growth(oos), "fixed_return": growth(fix),
            "trades": len(oos),
        })  # fmt: skip
    years = (end - first_oos).days / 365.25

    def total(parts: list[pd.Series]) -> dict:
        r = pd.concat(parts) if parts else pd.Series(dtype=float)
        g, dd = growth(r), closed_drawdown(r)
        cagr = (1 + g) ** (1 / years) - 1 if years > 0 else 0.0
        return {"return": g, "cagr": cagr, "drawdown": dd,
                "calmar": cagr / dd if dd > 0 else float("inf"), "trades": len(r)}  # fmt: skip

    return {"rows": rows, "picked": total(picked_parts), "fixed": total(fixed_parts),
            "oos_from": first_oos, "years": years}  # fmt: skip


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--slice", choices=["train"], required=True)  # never validation/test
    parser.add_argument("--strategy", nargs="+", default=DEFAULT_CANDIDATES)
    parser.add_argument("--fixed", default="TrendEma")
    parser.add_argument("--universe", choices=UNIVERSES, default="core")
    parser.add_argument("--fee", type=float, default=0.0015)
    parser.add_argument("--results-dir", type=Path, default=report.RESULTS_DIR)
    args = parser.parse_args()

    s = SLICES[args.slice]
    stats = report.latest_stats_per_strategy(
        s.timerange, universe_pairs(args.universe), args.fee, args.results_dir
    )
    missing = [n for n in args.strategy if n not in stats]
    if missing:
        raise SystemExit(f"no backtest result for {missing} on this slice/universe/fee: backtest them first")
    candidates = {
        n: trade_series(stats[n]["trades"], stats[n].get("starting_balance", 1000.0))
        for n in args.strategy
    }
    start, end = pd.Timestamp(s.start, tz="UTC"), pd.Timestamp(s.end, tz="UTC")
    r = walk_forward(candidates, start, end, args.fixed)

    print(f"Walk-forward, --timerange {s.timerange} (train only), universe {args.universe}")
    print(f"Choose on the previous {LOOKBACK_MONTHS} months, trade the next {STEP_MONTHS}. "
          f"Out-of-sample from {r['oos_from'].date()}. Drawdown = closed trades.")
    head = f"{'Window':<25}{'Chosen':<14}{'Trades':>7}{'Chosen ret':>11}{args.fixed + ' ret':>16}"
    print(head)
    print("-" * len(head))
    for row in r["rows"]:
        span = f"{row['from'].date()} -> {row['to'].date()}"
        print(f"{span:<25}{row['chosen']:<14}{row['trades']:>7}"
              f"{row['chosen_return']:>+11.1%}{row['fixed_return']:>+16.1%}")
    print()
    for label, t in (("Pick-the-best", r["picked"]), (f"Fixed {args.fixed}", r["fixed"])):
        warn = "  (<50 trades: weak evidence)" if t["trades"] < report.MIN_TRADES else ""
        print(f"{label:<18} trades {t['trades']:>4}  return {t['return']:+.1%}  CAGR {t['cagr']:+.1%}"
              f"  DD {t['drawdown']:.1%}  Calmar {t['calmar']:.2f}{warn}")


if __name__ == "__main__":
    main()
