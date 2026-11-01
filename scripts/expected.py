"""Forward check: is VolTarget's result on the fresh slice inside its expected range?

    python3 scripts/ft.py expected

The past tells us roughly how the rule behaves: some months it loses a bit, some it
wins a lot. This tool turns that into a range for the period we have seen since the
test slice ("fresh"): it resamples VolTarget's own daily returns from slices we have
already judged (validation core + early, kill switch off) in blocks of 7 days (so calm
and wild weeks stay together), 5000 times, each path as long as the fresh period. Then
it shows where the real fresh result falls in that range.

  inside 5%..95%   behaving like its history
  below 5%         worse than 95% of the simulated paths: early warning, look closer
  above 95%        better than usual (luck is possible too)

Judging only. Nothing is tuned on fresh data.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

STRATEGY = "TrendEmaVolTarget"
BLOCK = 7
RUNS = 5000
SEED = 7


def block_bootstrap(returns: np.ndarray, days: int, runs: int = RUNS, block: int = BLOCK, seed: int = SEED) -> np.ndarray:
    """runs x days matrix of daily returns resampled in contiguous blocks."""
    rng = np.random.default_rng(seed)
    n = len(returns)
    if n < block:
        raise ValueError("not enough history")
    out = np.empty((runs, days))
    for i in range(runs):
        path = []
        while len(path) < days:
            start = rng.integers(0, n - block + 1)
            path.extend(returns[start : start + block])
        out[i] = path[:days]
    return out


def path_stats(paths: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Total return and max drawdown of every simulated path."""
    eq = np.cumprod(1 + paths, axis=1)
    eq = np.hstack([np.ones((len(eq), 1)), eq])
    total = eq[:, -1] - 1
    dd = (1 - eq / np.maximum.accumulate(eq, axis=1)).max(axis=1)
    return total, dd


def percentile_of(values: np.ndarray, x: float) -> float:
    return float((values < x).mean())


def verdict(pct: float) -> str:
    if pct < 0.05:
        return "BELOW the expected range (worse than 95% of simulated paths): early warning"
    if pct > 0.95:
        return "above the expected range (better than usual)"
    return "inside the expected range"


def main() -> None:  # pragma: no cover - needs backtest results inside the container
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import benchmark
    import report
    from equity import build_curve
    from splits import SLICES

    def daily(sl: str, uni: str, d: Path) -> pd.Series | None:
        bh = benchmark.run(sl, "1h", 0.0015, universe=uni)
        st = report.latest_stats_per_strategy(SLICES[sl].timerange, benchmark.universe_pairs(uni), 0.0015, d).get(STRATEGY)
        if not st or not st.get("trades"):
            return None
        eq = build_curve(st["trades"], bh["closes"], st.get("starting_balance", 1000.0), bh["index"])["equity"]
        return eq.resample("1D").last().pct_change().dropna()

    nk = Path("/freqtrade/user_data/backtest_results/no_kill_switch")
    hist = [r for r in (daily("validation", "core", nk), daily("early", "early", report.RESULTS_DIR)) if r is not None]
    fresh = daily("fresh", "core", report.RESULTS_DIR)
    if not hist or fresh is None or fresh.empty:
        print("expected: missing results (run the validation/early/fresh backtests of TrendEmaVolTarget first)")
        return
    history = np.concatenate([h.to_numpy() for h in hist])
    days = len(fresh)
    total, dd = path_stats(block_bootstrap(history, days))
    f_total, f_dd = path_stats(fresh.to_numpy()[None, :])
    p_ret, p_dd = percentile_of(total, f_total[0]), percentile_of(dd, f_dd[0])
    print(f"Expected range for {STRATEGY}, core, {days} fresh days "
          f"(history: {len(history)} days of validation core + early, block {BLOCK}d, {RUNS} paths)")  # fmt: skip
    print(f"  return   5% {np.percentile(total, 5):+.1%}   median {np.median(total):+.1%}   95% {np.percentile(total, 95):+.1%}"
          f"   | fresh {f_total[0]:+.1%} at percentile {p_ret:.0%} -> {verdict(p_ret)}")  # fmt: skip
    print(f"  max DD   median {np.median(dd):.1%}   95% {np.percentile(dd, 95):.1%}   | fresh {f_dd[0]:.1%}"
          f" (worse than {p_dd:.0%} of paths)")  # fmt: skip
    print(f"expected_line: {days} gün, getiri {f_total[0]:+.1%} (beklenen aralık %5-%95: "
          f"{np.percentile(total, 5):+.1%} .. {np.percentile(total, 95):+.1%}, yüzdelik {p_ret:.0%}) -> "
          + ("BEKLENENİN ALTINDA, dikkat" if p_ret < 0.05 else "beklenenin üstünde" if p_ret > 0.95 else "beklenen aralıkta"))


if __name__ == "__main__":
    main()
