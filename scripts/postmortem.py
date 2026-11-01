"""Post-mortem of the final test slice (analysis only; the slice is used up, nothing here may change a rule).

    python3 scripts/ft.py postmortem

Month by month on the test slice (20250807-20261001, core 5, kill switch ON as backtested):
VolTarget and TrendEma closed-trade P/L, trades, win rate, stop vs signal exits; the BTC
regime mix of the month (regimes.py labels); month returns of VolTarget, TrendEma, TSMOM,
weekly DCA and buy-and-hold. Prints Markdown tables for docs/research/10.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

STRATS = ("TrendEmaVolTarget", "TrendEma")


def monthly_trades(trades: list[dict]):
    """DataFrame by close month: trades, P/L, win rate, stop exits, signal exits."""
    import pandas as pd

    df = pd.DataFrame(trades)
    df["month"] = pd.to_datetime(df["close_date"], utc=True).dt.strftime("%Y-%m")
    g = df.groupby("month")
    return pd.DataFrame({
        "trades": g.size(),
        "pl": g["profit_abs"].sum(),
        "win": g["profit_abs"].apply(lambda s: (s > 0).mean()),
        "stops": g["exit_reason"].apply(lambda s: (s == "stop_loss").sum()),
        "signal": g["exit_reason"].apply(lambda s: (s == "ema_cross_down").sum()),
    })  # fmt: skip


def month_returns(equity):
    m = equity.resample("ME").last()
    return m.pct_change().fillna(m.iloc[0] / equity.iloc[0] - 1)


def main() -> None:  # pragma: no cover - needs data and backtest results inside the container
    import pandas as pd

    import benchmark
    import bots
    import regimes
    import report
    from benchmark import DATA_DIR, dca_equity
    from equity import build_curve
    from splits import SLICES

    s = SLICES["test"]
    bh = benchmark.run("test", "1h", 0.0015, universe="core")
    stats = report.latest_stats_per_strategy(s.timerange, benchmark.universe_pairs("core"), 0.0015, report.RESULTS_DIR)
    prices = pd.DataFrame(bh["closes"]).reindex(bh["index"]).ffill()
    curves = {
        "Buy & hold": (prices / prices.bfill().iloc[0]).mean(axis=1),
        "Weekly DCA": dca_equity(bh["closes"], 0.0015),
        "TSMOM": bots.tsmom_bot("test", "core", 0.0015, start=bh["index"][0])["equity"],
    }
    for name in STRATS:
        st = stats[name]
        curves[name] = build_curve(st["trades"], bh["closes"], st.get("starting_balance", 1000.0), bh["index"])["equity"]
    rets = pd.DataFrame({k: month_returns(v) for k, v in curves.items()})
    rets.index = rets.index.strftime("%Y-%m")

    btc = pd.read_feather(DATA_DIR / "BTC_USDT-1d.feather").set_index("date")["close"]
    lab = regimes.hourly_labels(regimes.label_days(btc), bh["index"])
    reg = lab.groupby(lab.index.strftime("%Y-%m"))["trend"].apply(lambda x: x.value_counts(normalize=True)).unstack().fillna(0)

    print("## Aylık getiri (ay sonu değer, kill switch açık)\n")
    print("| Ay | BTC rejimi (boğa/yatay/ayı) | VolTarget | TrendEma | TSMOM | Haftalık DCA | Al-tut |")
    print("|---|---|---|---|---|---|---|")
    for m, r in rets.iterrows():
        g = reg.loc[m] if m in reg.index else {}
        mix = "/".join(f"{g.get(k, 0) * 100:.0f}" for k in ("bull", "sideways", "bear"))
        print(f"| {m} | {mix} | {r['TrendEmaVolTarget']:+.1%} | {r['TrendEma']:+.1%} | {r['TSMOM']:+.1%} "
              f"| {r['Weekly DCA']:+.1%} | {r['Buy & hold']:+.1%} |")  # fmt: skip
    for name in STRATS:
        mt = monthly_trades(stats[name]["trades"])
        print(f"\n## {name}: kapanan işlemler (kapanış ayına göre)\n")
        print("| Ay | İşlem | K/Z USDT | Kazanan | Stop çıkışı | Sinyal çıkışı |")
        print("|---|---|---|---|---|---|")
        for m, r in mt.iterrows():
            print(f"| {m} | {r['trades']} | {r['pl']:+.1f} | %{r['win'] * 100:.0f} | {r['stops']} | {r['signal']} |")
        tot = mt.sum()
        print(f"| **Toplam** | {int(tot['trades'])} | {tot['pl']:+.1f} | | {int(tot['stops'])} | {int(tot['signal'])} |")
    # whole-slice regime mix and per-regime results of each curve
    print("\n## Rejime göre (bütün test dilimi, saatlerin getirisi yıla çevrilmiş)\n")
    print("| | " + " | ".join(regimes.TR[k] for k in regimes.TRENDS) + " |")
    print("|---|" + "---|" * len(regimes.TRENDS))
    share = lab["trend"].value_counts(normalize=True)
    print("| zamanın payı | " + " | ".join(f"%{share.get(k, 0) * 100:.0f}" for k in regimes.TRENDS) + " |")
    for name, eq in curves.items():
        rs = regimes.regime_stats(eq, lab["trend"])
        print(f"| {name} | " + " | ".join(f"{rs[k]['per_year']:+.0%}" if k in rs else "-" for k in regimes.TRENDS) + " |")


if __name__ == "__main__":
    main()
