"""When does a bot make and lose money? Results split by market regime (analysis only).

    python3 scripts/ft.py regimes --slice train --no-kill-switch
    python3 scripts/ft.py regimes --slice early --universe early

Every hour gets the regime of the last CLOSED BTC daily candle:
  trend:  bull     close > SMA200 and SMA200 rising (higher than 20 days ago)
          bear     close < SMA200 and SMA200 falling
          sideways everything else
  vol:    low / mid / high = tercile of BTC's 30-day daily volatility inside the slice
For each bot: compounded return of the hours spent in each regime, that return per
year, the worst fall when only those hours are stitched together, time in market,
and (Freqtrade strategies only) trade count and win rate by the regime at entry.
Only train and early are allowed: nothing here is used to tune, ideas go to a backlog.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

SMA, SLOPE_DAYS, VOL_DAYS = 200, 20, 30
TRENDS, VOLS = ["bull", "sideways", "bear"], ["low", "mid", "high"]
TR = {"bull": "boğa", "sideways": "yatay/testere", "bear": "ayı", "low": "düşük oynaklık", "mid": "orta oynaklık",
      "high": "yüksek oynaklık"}  # fmt: skip


def label_days(btc_daily: pd.Series) -> pd.DataFrame:
    """Trend and volatility regime per BTC day (label known at that day's close)."""
    sma = btc_daily.rolling(SMA).mean()
    rising = sma > sma.shift(SLOPE_DAYS)
    falling = sma < sma.shift(SLOPE_DAYS)
    trend = np.where((btc_daily > sma) & rising, "bull", np.where((btc_daily < sma) & falling, "bear", "sideways"))
    vol = np.log(btc_daily).diff().rolling(VOL_DAYS).std() * np.sqrt(365)
    out = pd.DataFrame({"trend": trend, "vol30": vol}, index=btc_daily.index)
    return out[sma.shift(SLOPE_DAYS).notna() & vol.notna()]  # slope needs 20 days of SMA200 history


def hourly_labels(days: pd.DataFrame, index: pd.DatetimeIndex) -> pd.DataFrame:
    """Each hour takes the label of the last day that had CLOSED before it (day D is known from D+1 00:00)."""
    known = days.copy()
    known.index = known.index + pd.Timedelta(days=1)
    lab = known.reindex(index, method="ffill")
    cuts = lab["vol30"].quantile([1 / 3, 2 / 3]).to_numpy()
    lab["vol"] = np.where(lab["vol30"] <= cuts[0], "low", np.where(lab["vol30"] <= cuts[1], "mid", "high"))
    lab.loc[lab["vol30"].isna(), "vol"] = None
    return lab


def regime_stats(equity: pd.Series, labels: pd.Series, invested: pd.Series | None = None) -> dict[str, dict]:
    """Per regime: return of its hours, that per year, max fall of the stitched hours, time in market."""
    ret = equity.pct_change().fillna(0.0)
    out = {}
    for name in labels.dropna().unique():
        mask = (labels == name).to_numpy()
        r = ret[mask]
        if len(r) == 0:
            continue
        curve = (1 + r).cumprod()
        total = float(curve.iloc[-1] - 1)
        out[name] = {
            "hours": int(mask.sum()),
            "share": float(mask.mean()),
            "return": total,
            "per_year": float((1 + total) ** (24 * 365 / len(r)) - 1),
            "max_drawdown": float((1 - curve / curve.cummax().clip(lower=1.0)).max()),
            "in_market": float((invested[mask] / equity[mask]).mean()) if invested is not None else None,
        }
    return out


def trade_stats(trades: list[dict], labels: pd.Series) -> dict[str, dict]:
    """Trade count and win rate by the regime at the entry hour."""
    out: dict[str, dict] = {}
    for t in trades:
        opened = pd.Timestamp(t["open_date"])
        opened = opened.tz_localize("UTC") if opened.tzinfo is None else opened
        pos = labels.index.searchsorted(opened.floor("1h"), side="right") - 1
        if pos < 0 or pd.isna(labels.iloc[pos]):
            continue
        d = out.setdefault(labels.iloc[pos], {"trades": 0, "wins": 0})
        d["trades"] += 1
        d["wins"] += int(t["profit_abs"] > 0)
    for d in out.values():
        d["win_rate"] = d["wins"] / d["trades"]
    return out


def render(title: str, kind: str, names: list[str], stats: dict, trades: dict) -> str:
    order = TRENDS if kind == "trend" else VOLS
    share = next(iter(stats.values()), {})
    head = f"{title} | " + ", ".join(f"{TR[g]} %{share[g]['share'] * 100:.0f}" for g in order if g in share)
    lines = [head, "", "| Bot | " + " | ".join(TR[g] for g in order) + " |", "|---|" + "---|" * len(order)]
    for n in names:
        cells = []
        for g in order:
            s = stats[n].get(g)
            if not s:
                cells.append("-")
                continue
            cell = f"{s['per_year']:+.0%}/yıl, düşüş {s['max_drawdown']:.0%}"
            if s["in_market"] is not None:
                cell += f", piyasada {s['in_market']:.0%}"
            t = trades.get(n, {}).get(g)
            if t:
                cell += f", {t['trades']} işlem %{t['win_rate'] * 100:.0f} kazanç"
            cells.append(cell)
        lines.append(f"| {n} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> None:  # pragma: no cover - needs data and backtest results inside the container
    import bots
    import report
    from benchmark import DATA_DIR, DEFAULT_FEE, dca_equity, universe_pairs
    from benchmark import run as benchmark_run
    from equity import build_curve
    from splits import SLICES

    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--slice", choices=["train", "early"], required=True)
    p.add_argument("--universe", default="core")
    p.add_argument("--strategy", nargs="*", default=["TrendEma", "TrendEmaVolTarget"])
    p.add_argument("--results-dir", type=Path, default=report.RESULTS_DIR)
    a = p.parse_args()
    fee, s = DEFAULT_FEE, SLICES[a.slice]
    bh = benchmark_run(a.slice, "1h", fee, universe=a.universe)
    prices = pd.DataFrame(bh["closes"]).reindex(bh["index"]).ffill()
    curves = {"Buy & hold": ((prices / prices.bfill().iloc[0]).mean(axis=1), None, [])}  # equal money per coin
    curves["Weekly DCA"] = (dca_equity(bh["closes"], fee), None, [])
    curves["Grid bot"] = (bots.simulate_bot(lambda c, cash, fee: bots.grid.simulate_pair(c, cash, fee=fee),
                                            a.slice, a.universe, fee)["equity"], None, [])  # fmt: skip
    curves["DCA bot (3Commas)"] = (bots.simulate_bot(bots.dcabot.simulate_pair, a.slice, a.universe, fee)["equity"], None, [])
    curves["TSMOM"] = (bots.tsmom_bot(a.slice, a.universe, fee, start=bh["index"][0])["equity"], None, [])
    stats = report.latest_stats_per_strategy(s.timerange, universe_pairs(a.universe), fee, a.results_dir)
    for name in a.strategy:
        st = stats.get(name)
        if not st:
            print(f"(no backtest result for {name}: backtest it first)")
            continue
        c = build_curve(st.get("trades", []), bh["closes"], st.get("starting_balance", 1000.0), bh["index"])
        curves[name] = (c["equity"], c["invested"], st.get("trades", []))
    btc = pd.read_feather(DATA_DIR / "BTC_USDT-1d.feather").set_index("date")["close"]
    for kind in ("trend", "vol"):
        res, trd = {}, {}
        for name, (eq, inv, trades) in curves.items():
            lab = hourly_labels(label_days(btc), eq.index)[kind]
            res[name] = regime_stats(eq, lab, inv)
            if trades:
                trd[name] = trade_stats(trades, lab)
        print(render(f"{a.slice} {a.universe} {kind}", kind, list(curves), res, trd))
        print()


if __name__ == "__main__":
    main()
