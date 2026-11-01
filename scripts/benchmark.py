"""Buy-and-hold benchmark: "what if we had bought at the start and never touched it?"

Splits the capital equally across the pairs, buys at the first candle of the
slice, sells at the last one, and pays the fee on both sides. Reports the same
risk numbers we judge strategies by.

    .venv/bin/python scripts/benchmark.py --slice train
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


def run(
    slice_name: str, timeframe: str, fee: float, data_dir: Path = DATA_DIR, universe: str = "core"
) -> dict:
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
    result = summarize(buy_and_hold_equity(closes, fee))
    result.update(
        slice=slice_name, timerange=s.timerange, pairs=list(closes), skipped=skipped, fee=fee
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--slice", choices=["train", "validation", "test"], required=True)
    parser.add_argument("--timeframe", default="1h")
    parser.add_argument("--fee", type=float, default=DEFAULT_FEE)
    parser.add_argument("--universe", choices=UNIVERSES, default="core")
    args = parser.parse_args()

    r = run(args.slice, args.timeframe, args.fee, universe=args.universe)
    print(f"Buy-and-hold benchmark, {r['slice']} slice (--timerange {r['timerange']})")
    print(f"Pairs: {', '.join(r['pairs'])}  equal weight, fee {r['fee']:.2%} per side")
    print(f"Period:        {r['start']} -> {r['end']}")
    print(f"Total return:  {r['total_return']:+.1%}")
    print(f"CAGR:          {r['cagr']:+.1%}  (yearly growth rate)")
    print(f"Max drawdown:  {r['max_drawdown']:.1%}  (worst fall from a peak)")
    print(f"Calmar:        {r['calmar']:.2f}  (CAGR / max drawdown)")


if __name__ == "__main__":
    main()
