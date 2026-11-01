"""Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014): is the edge real after N trials?

    docker compose run --rm -v "$PWD/scripts:/freqtrade/scripts:ro" --entrypoint python \\
        freqtrade /freqtrade/scripts/deflated.py

We tried many rules. The best of many tries looks good partly by luck. The DSR asks:
given the Sharpe ratio we measured, its skew/kurtosis, the sample length T, the
number of trials N and how much the trials' Sharpe ratios varied, what is the
probability that the true Sharpe is above zero? DSR >= 0.95 = the edge survives.

All Sharpe ratios here are per period (daily), not annualized.
"""

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

EULER_GAMMA = 0.5772156649015329


def norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def norm_ppf(p: float) -> float:
    """Inverse standard normal (Acklam's rational approximation, |error| < 1.2e-9)."""
    a = [-3.969683028665376e01, 2.209460984245205e02, -2.759285104469687e02, 1.383577518672690e02, -3.066479806614716e01, 2.506628277459239e00]
    b = [-5.447609879822406e01, 1.615858368580409e02, -1.556989798598866e02, 6.680131188771972e01, -1.328068155288572e01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e00, -2.549732539343734e00, 4.374664141464968e00, 2.938163982698783e00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00, 3.754408661907416e00]
    lo, hi = 0.02425, 1 - 0.02425
    if p < lo:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > hi:
        return -norm_ppf(1 - p)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def expected_max_sharpe(var_sr: float, n_trials: int) -> float:
    """SR0: the Sharpe the best of N unskilled trials would show by luck (eq. in the paper)."""
    return math.sqrt(var_sr) * ((1 - EULER_GAMMA) * norm_ppf(1 - 1 / n_trials)
                                + EULER_GAMMA * norm_ppf(1 - 1 / (n_trials * math.e)))  # fmt: skip


def psr(sr: float, sr0: float, t: int, skew: float, kurt: float) -> float:
    """Probabilistic Sharpe Ratio: P(true SR > sr0). kurt = ordinary (not excess) kurtosis."""
    den = math.sqrt(1 - skew * sr + (kurt - 1) / 4 * sr * sr)
    return norm_cdf((sr - sr0) * math.sqrt(t - 1) / den)


def dsr(returns: pd.Series, var_sr: float, n_trials: int) -> dict:
    r = returns.dropna()
    sr = float(r.mean() / r.std(ddof=1))
    skew = float(r.skew())
    kurt = float(r.kurt()) + 3  # pandas gives excess kurtosis
    sr0 = expected_max_sharpe(var_sr, n_trials)
    return {"sr": sr, "sr_annual": sr * math.sqrt(365), "skew": skew, "kurt": kurt, "t": len(r),
            "sr0": sr0, "dsr": psr(sr, sr0, len(r), skew, kurt)}  # fmt: skip


def daily_returns(equity: pd.Series) -> pd.Series:
    return equity.resample("1D").last().pct_change().dropna()


def main() -> None:  # pragma: no cover - needs backtest results inside the container
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import benchmark
    import report
    from equity import build_curve
    from splits import SLICES

    if len(sys.argv) < 2:
        raise SystemExit("usage: deflated.py N   (python3 scripts/ft.py deflated reads N from docs/trials.csv)")
    n_trials = int(sys.argv[1])
    nk = Path("/freqtrade/user_data/backtest_results/no_kill_switch")
    cases = [("validation", "core", nk), ("validation", "wide", nk), ("early", "early", report.RESULTS_DIR)]
    for sl, uni, d in cases:
        s = SLICES[sl]
        bh = benchmark.run(sl, "1h", 0.0015, universe=uni)
        stats = report.latest_stats_per_strategy(s.timerange, benchmark.universe_pairs(uni), 0.0015, d)
        srs, rets = {}, {}
        for name, st in stats.items():
            if not st.get("trades"):
                continue
            eq = build_curve(st["trades"], bh["closes"], st.get("starting_balance", 1000.0), bh["index"])["equity"]
            r = daily_returns(eq)
            if r.std() > 0:
                srs[name], rets[name] = float(r.mean() / r.std()), r
        var_sr = float(np.var(list(srs.values()), ddof=1)) if len(srs) > 2 else float("nan")
        print(f"\n== {sl} {uni}  --timerange {s.timerange}: {len(srs)} strategies with results here, "
              f"variance of their daily Sharpe = {var_sr:.6f}, N = {n_trials}")  # fmt: skip
        for name in ("TrendEmaVolTarget", "TrendEmaVolTargetCooldown24", "TrendEmaVolTargetDerisk72h", "TrendEma"):
            if name not in rets:
                print(f"  {name}: no result")
                continue
            o = dsr(rets[name], var_sr, n_trials)
            verdict = "survives (>= 0.95)" if o["dsr"] >= 0.95 else "may be luck (< 0.95)"
            print(f"  {name:<18} SR/day {o['sr']:.4f} (ann. {o['sr_annual']:.2f})  skew {o['skew']:+.2f}  kurt {o['kurt']:.1f}  "
                  f"T {o['t']}  SR0 {o['sr0']:.4f}  DSR {o['dsr']:.3f}  -> {verdict}")  # fmt: skip


if __name__ == "__main__":
    main()
