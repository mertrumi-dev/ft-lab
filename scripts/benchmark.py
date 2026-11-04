"""Buy-and-hold benchmark: "what if we had bought at the start and never touched it?"

Splits the capital equally across the pairs, buys at the first candle of the
slice, sells at the last one, and pays the fee on both sides. Reports the same
risk numbers we judge strategies by.

    python3 scripts/ft.py benchmark --slice train
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from splits import SLICES  # noqa: E402
from universe import UNIVERSES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT / "user_data" / "config" / "config.json"
DATA_DIR = ROOT / "user_data" / "data" / "binance"
DEFAULT_FEE = 0.0015  # 0.1% commission + 0.05% slippage, per side


def load_closes(pair: str, timeframe: str, data_dir: Path = DATA_DIR) -> pd.Series:
    """Close prices indexed by date, from Freqtrade's downloaded feather file."""
    path = data_dir / f"{pair.replace('/', '_')}-{timeframe}.feather"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Download data first (see README).")
    df = pd.read_feather(path)
    return df.set_index("date")["close"]


def buy_and_hold_equity(closes: dict[str, pd.Series], fee: float) -> pd.Series:
    """Portfolio value over time, starting at 1.0, equal weight per pair."""
    frame = pd.DataFrame(closes).dropna()
    if frame.empty:
        raise ValueError("no overlapping data for these pairs in this slice")
    weight = 1.0 / frame.shape[1]
    units = weight * (1 - fee) / frame.iloc[0]  # coins bought with each pair's share
    equity = (frame * units).sum(axis=1)
    equity.iloc[-1] *= 1 - fee  # selling at the end costs the fee too
    return equity


def dca_equity(closes: dict[str, pd.Series], fee: float, every: str = "W") -> pd.Series:
    """DCA (regular buying): same starting money, but spent in equal parts over the slice.

    The capital (1.0) starts as cash. On the first candle of each `every` period
    (default: each calendar week, Monday) an equal part is spent, split equally across the pairs.
    The last part is spent in the last period, so at the end everything is in
    coins. Like buy-and-hold, everything is sold at the last candle (fee paid).
    Cash earns nothing here; a savings account would add interest on it.
    """
    frame = pd.DataFrame(closes).dropna()
    if frame.empty:
        raise ValueError("no overlapping data for these pairs in this slice")
    # Calendar periods ("W" = Monday-Sunday weeks), not 7-day blocks from 1970.
    periods = frame.index.tz_localize(None).to_period(every)
    buy_rows = ~periods.duplicated()  # first candle of every period
    n_buys = int(buy_rows.sum())
    per_pair = 1.0 / n_buys / frame.shape[1]  # cash spent on each pair per buy
    bought = (per_pair * (1 - fee) / frame).mul(buy_rows.astype(float), axis=0)
    units = bought.cumsum()  # coins owned after each candle
    cash = 1.0 - pd.Series(buy_rows.astype(float), index=frame.index).cumsum() / n_buys
    equity = (frame * units).sum(axis=1) + cash
    equity.iloc[-1] = (frame.iloc[-1] * units.iloc[-1]).sum() * (1 - fee) + cash.iloc[-1]
    return equity


def invested_ratio(curve: pd.DataFrame) -> pd.Series:
    """Share of the account in coins each hour: open position value / total equity (equity.build_curve)."""
    return (curve["invested"] / curve["equity"]).clip(0.0, 1.0)


def exposure_matched_equity(closes: dict[str, pd.Series], ratio: pd.Series, fee: float, charge_turnover: bool = False) -> pd.Series:
    """Buy-and-hold scaled by a strategy's own hourly invested ratio; the rest is cash at 0%.

    Answers: "the same amount of money in the market in the same hours, but the whole equal-weight
    basket instead of the coins the strategy picked: what would it have earned?" It still carries
    the strategy's in/out timing; a constant ratio (its mean) is the version with no timing at all.
    Each hour earns ratio(previous hour) x the basket's return: the previous hour, so the benchmark
    never uses a ratio it could not have known yet. Ratio 0 always = return 0; ratio 1 always =
    buy_and_hold_equity exactly.

    Fees: like buy-and-hold, once in and once out, on the average invested share. That is kind to
    the benchmark (following the ratio hour by hour would really cost more), so it makes the
    strategy's comparison harder. charge_turnover=True instead pays the fee on every change of the
    ratio, plus the first buy and the last sale: the other end of the honest range.
    """
    basket = buy_and_hold_equity(closes, 0.0)
    r = ratio.reindex(basket.index).fillna(0.0).clip(0.0, 1.0)
    equity = (1 + r.shift(1).fillna(0.0) * basket.pct_change().fillna(0.0)).cumprod()
    if charge_turnover:
        trades = r.diff().abs().fillna(r.iloc[0])
        trades.iloc[-1] += r.iloc[-1]
        return equity * (1 - fee * trades).cumprod()
    average = float(r.mean())
    equity *= 1 - fee * average
    equity.iloc[-1] *= 1 - fee * average
    return equity


def max_drawdown(equity: pd.Series) -> float:
    """Largest fall from a peak, as a positive ratio (0.5 = -50%)."""
    return float((1 - equity / equity.cummax()).max())


def summarize(equity: pd.Series) -> dict:
    total = float(equity.iloc[-1] / equity.iloc[0] - 1)
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = (1 + total) ** (1 / years) - 1 if years > 0 else 0.0
    mdd = max_drawdown(equity)
    return {
        "start": str(equity.index[0].date()),
        "end": str(equity.index[-1].date()),
        "total_return": total,
        "cagr": cagr,
        "max_drawdown": mdd,
        "calmar": cagr / mdd if mdd > 0 else float("inf"),
    }


def universe_pairs(universe: str = "core") -> list[str]:
    pairs = UNIVERSES[universe]
    return pairs if pairs else json.loads(CONFIG_FILE.read_text())["exchange"]["pair_whitelist"]


def by_year(equity: pd.Series) -> dict[int, dict]:
    """Return and worst fall inside each calendar year (for 'how did it do in 2022?')."""
    out = {}
    for year, part in equity.groupby(equity.index.year):
        out[int(year)] = {
            "return": float(part.iloc[-1] / part.iloc[0] - 1),
            "max_drawdown": max_drawdown(part),
        }
    return out


def load_slice_closes(
    slice_name: str, timeframe: str, data_dir: Path = DATA_DIR, universe: str = "core"
) -> tuple[dict[str, pd.Series], list[str]]:
    """Close prices of every pair in the universe, cut to the slice. Missing wide pairs are skipped."""
    s = SLICES[slice_name]
    pairs = universe_pairs(universe)
    start = pd.Timestamp(s.start, tz="UTC")
    end = pd.Timestamp(s.end, tz="UTC")
    closes, skipped = {}, []
    for pair in pairs:
        try:
            series = load_closes(pair, timeframe, data_dir)
        except FileNotFoundError:
            if universe == "core":
                raise  # core coins must always have data
            skipped.append(pair)  # e.g. delisted from Binance, nothing to download
            continue
        closes[pair] = series[(series.index >= start) & (series.index < end)]
    return closes, skipped


def window_warning(slice_start, index) -> str | None:
    """Buy & hold only starts when EVERY coin has data. If one coin was listed late
    (e.g. APE in 2022), the comparison window is shorter than the slice: say so loudly."""
    first = index[0]
    if first.date() > slice_start:
        return (f"WARNING: buy & hold starts {first.date()}, not {slice_start} (a coin was listed later). "
                f"Return/CAGR from Freqtrade cover the whole slice; compare with the bots table "
                f"(same window for every row) instead.")
    return None


def run(
    slice_name: str, timeframe: str, fee: float, data_dir: Path = DATA_DIR, universe: str = "core"
) -> dict:
    s = SLICES[slice_name]
    closes, skipped = load_slice_closes(slice_name, timeframe, data_dir, universe)
    equity = buy_and_hold_equity(closes, fee)
    result = summarize(equity)
    result["years"] = by_year(equity)
    result.update(
        slice=slice_name, timerange=s.timerange, pairs=list(closes), skipped=skipped, fee=fee
    )
    result["closes"] = closes  # reused by report.py for hourly strategy equity
    result["index"] = equity.index
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--slice", choices=["train", "validation", "test", "fresh", "early"], required=True)
    parser.add_argument("--timeframe", default="1h")
    parser.add_argument("--fee", type=float, default=DEFAULT_FEE)
    parser.add_argument("--universe", choices=UNIVERSES, default="core")
    args = parser.parse_args()

    r = run(args.slice, args.timeframe, args.fee, universe=args.universe)
    dca = summarize(dca_equity(r["closes"], args.fee))
    print(f"Buy-and-hold benchmark, {r['slice']} slice (--timerange {r['timerange']})")
    print(f"Pairs: {', '.join(r['pairs'])}  equal weight, fee {r['fee']:.2%} per side")
    print(f"Period:        {r['start']} -> {r['end']}")
    print(f"Total return:  {r['total_return']:+.1%}")
    print(f"CAGR:          {r['cagr']:+.1%}  (yearly growth rate)")
    print(f"Max drawdown:  {r['max_drawdown']:.1%}  (worst fall from a peak)")
    print(f"Calmar:        {r['calmar']:.2f}  (CAGR / max drawdown)")
    print()
    print("DCA: same money, spent in equal weekly parts over the slice")
    print(f"Total return:  {dca['total_return']:+.1%}")
    print(f"CAGR:          {dca['cagr']:+.1%}")
    print(f"Max drawdown:  {dca['max_drawdown']:.1%}")
    print(f"Calmar:        {dca['calmar']:.2f}")


if __name__ == "__main__":
    main()
