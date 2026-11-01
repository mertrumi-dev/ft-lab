"""Forward risk: what may the next 12 months look like for the live rule, with the latching kill switch?

    python3 scripts/ft.py forward-risk

The rule's own daily returns from slices we have already judged (validation core with the
kill switch off + early) are resampled in 7-day blocks (expected.py's block bootstrap),
10,000 paths of 365 days. On each path the kill switch latches the first day equity is 20%
below its peak; from then on the path is flat (no new trades, R13).

Approximation, stated plainly: the real kill switch looks at REALIZED equity (closed trades);
these paths are mark-to-market (open trades included), which usually falls at least as deep.
So the kill-switch probabilities here lean high (cautious).
Compared with TrendEma and buy-and-hold of the same coins (buy-and-hold has no kill switch:
its row says how often it would have been 20% down). Judging only, nothing is tuned.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from expected import block_bootstrap  # noqa: E402

KILL = 0.20
DAYS = 365
RUNS = 10_000
HORIZONS = {"3 ay": 91, "6 ay": 182, "12 ay": 365}


def latch_paths(paths: np.ndarray, kill: float | None = KILL) -> tuple[np.ndarray, np.ndarray]:
    """Equity (runs x days+1, starting at 1) with the kill switch latched, and the latch day (-1 = never).

    The day the fall from the peak reaches `kill` is the last day that moves; afterwards flat.
    """
    eq = np.hstack([np.ones((len(paths), 1)), np.cumprod(1 + paths, axis=1)])
    latch = np.full(len(paths), -1)
    if kill is None:
        return eq, latch
    dd = 1 - eq / np.maximum.accumulate(eq, axis=1)
    hit = dd >= kill
    has = hit.any(axis=1)
    first = np.where(has, hit.argmax(axis=1), -1)
    for i in np.nonzero(has)[0]:
        eq[i, first[i] + 1 :] = eq[i, first[i]]
    return eq, first


def longest_underwater(eq: np.ndarray) -> np.ndarray:
    """Per path: the longest unbroken run of days below the previous peak (drawdown duration)."""
    under = eq < np.maximum.accumulate(eq, axis=1)
    best = np.zeros(len(eq), dtype=int)
    run = np.zeros(len(eq), dtype=int)
    for d in range(eq.shape[1]):
        run = np.where(under[:, d], run + 1, 0)
        best = np.maximum(best, run)
    return best


def stats(paths: np.ndarray, kill: float | None = KILL) -> dict:
    eq, latch = latch_paths(paths, kill)
    total = eq[:, -1] - 1
    out = {"median": float(np.median(total)), "worst5": float(np.percentile(total, 5)),
           "p_loss": float((total < 0).mean()), "underwater_days": float(np.median(longest_underwater(eq)))}  # fmt: skip
    dd_hit = (1 - eq / np.maximum.accumulate(eq, axis=1)) >= KILL
    for name, d in HORIZONS.items():
        out[f"p_kill_{name}"] = float((dd_hit[:, : d + 1].any(axis=1)).mean())
    return out


def render(rows: dict[str, dict], history_days: dict[str, int]) -> str:
    head = f"{'':<22}{'kill 3 ay':>10}{'6 ay':>7}{'12 ay':>7}{'12 ay ortanca':>15}{'en kötü %5':>12}{'zarar ihtimali':>16}{'en uzun zirve altı':>20}"
    lines = [f"Forward risk, {RUNS} paths x {DAYS} days, 7-day blocks (history: "
             + ", ".join(f"{k} {v}d" for k, v in history_days.items()) + ")", head]  # fmt: skip
    for name, r in rows.items():
        lines.append(f"{name:<22}{r['p_kill_3 ay']:>10.1%}{r['p_kill_6 ay']:>7.1%}{r['p_kill_12 ay']:>7.1%}"
                     f"{r['median']:>+15.1%}{r['worst5']:>+12.1%}{r['p_loss']:>16.1%}{r['underwater_days']:>17.0f} gün")  # fmt: skip
    v = rows.get("TrendEmaVolTarget")
    if v:
        lines.append(f"forward_line: VolTarget önümüzdeki 12 ay (geçmişten 10.000 senaryo): ortanca {v['median']:+.0%}, "
                     f"kötü %5'lik dilim {v['worst5']:+.0%}, zarar ihtimali %{v['p_loss'] * 100:.0f}, "
                     f"kill switch ihtimali %{v['p_kill_12 ay'] * 100:.0f} (tahmin değil, geçmişin tekrar karıştırılması)")  # fmt: skip
    return "\n".join(lines)


def main() -> None:  # pragma: no cover - needs backtest results inside the container
    import pandas as pd

    import benchmark
    import report
    from equity import build_curve
    from splits import SLICES

    nk = Path("/freqtrade/user_data/backtest_results/no_kill_switch")
    cases = (("validation", "core", nk), ("early", "early", report.RESULTS_DIR))
    hist: dict[str, list[np.ndarray]] = {"TrendEmaVolTarget": [], "TrendEma": [], "Buy & hold (same coins)": []}
    days = {}
    for sl, uni, d in cases:
        bh = benchmark.run(sl, "1h", 0.0015, universe=uni)
        prices = pd.DataFrame(bh["closes"]).reindex(bh["index"]).ffill()
        bh_eq = (prices / prices.bfill().iloc[0]).mean(axis=1)
        hist["Buy & hold (same coins)"].append(bh_eq.resample("1D").last().pct_change().dropna().to_numpy())
        stats_ = report.latest_stats_per_strategy(SLICES[sl].timerange, benchmark.universe_pairs(uni), 0.0015, d)
        for name in ("TrendEmaVolTarget", "TrendEma"):
            st = stats_.get(name)
            if st and st.get("trades"):
                eq = build_curve(st["trades"], bh["closes"], st.get("starting_balance", 1000.0), bh["index"])["equity"]
                hist[name].append(eq.resample("1D").last().pct_change().dropna().to_numpy())
        days[f"{sl} {uni}"] = len(bh_eq.resample("1D").last()) - 1
    rows = {}
    for name, parts in hist.items():
        if not parts:
            continue
        r = np.concatenate(parts)
        rows[name] = stats(block_bootstrap(r, DAYS, runs=RUNS), None if name.startswith("Buy") else KILL)
    print(render(rows, days))


if __name__ == "__main__":
    main()
