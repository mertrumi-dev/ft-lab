"""Safe wrapper around Freqtrade commands for ft-lab.

Why a wrapper: it takes dates ONLY from scripts/splits.py, always uses the
realistic fee, refuses to hyperopt on anything but the train slice, and logs
every run to docs/experiments.md so we can count how many times we tried.

    .venv/bin/python scripts/ft.py download
    .venv/bin/python scripts/ft.py backtest --slice train
    .venv/bin/python scripts/ft.py backtest --slice validation
    .venv/bin/python scripts/ft.py backtest --slice test --final-test   # once per strategy!
    .venv/bin/python scripts/ft.py hyperopt --epochs 200 --spaces buy sell
"""

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from splits import DATA_START, SLICES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
EXPERIMENTS_LOG = ROOT / "docs" / "experiments.md"
CONFIG = "/freqtrade/user_data/config/config.json"  # path inside the container
FEE = "0.0015"
DEFAULT_STRATEGY = "TrendEma"
# Extra months before DATA_START so EMA200 has warm-up candles.
DOWNLOAD_FROM = f"{DATA_START.year - 1}1001"


def docker_cmd(*args: str) -> list[str]:
    return ["docker", "compose", "run", "--rm", "freqtrade", *args]


def build_command(args: argparse.Namespace) -> list[str]:
    if args.command == "download":
        return docker_cmd(
            "download-data", "--config", CONFIG,
            "--timerange", f"{DOWNLOAD_FROM}-",
            "--timeframes", "1h", "4h",
        )  # fmt: skip

    if args.command == "backtest":
        if args.slice == "test" and not args.final_test:
            raise SystemExit(
                "Refusing: the test slice is the final exam. Use it ONCE per strategy, "
                "after train and validation are done, and add --final-test."
            )
        return docker_cmd(
            "backtesting", "--config", CONFIG,
            "--strategy", args.strategy,
            "--timerange", SLICES[args.slice].timerange,
            "--fee", FEE,
            "--export", "trades",
        )  # fmt: skip

    if args.command == "hyperopt":
        # Hyperopt only ever sees the train slice. There is no option to change it.
        return docker_cmd(
            "hyperopt", "--config", CONFIG,
            "--strategy", args.strategy,
            "--timerange", SLICES["train"].timerange,
            "--fee", FEE,
            "--hyperopt-loss", "CalmarHyperOptLoss",
            "--epochs", str(args.epochs),
            "--spaces", *args.spaces,
        )  # fmt: skip

    raise SystemExit(f"unknown command {args.command}")


def log_run(args: argparse.Namespace, cmd: list[str]) -> None:
    if args.command == "download":
        return
    if not EXPERIMENTS_LOG.exists():
        EXPERIMENTS_LOG.write_text(
            "# Deneme kaydı\n\nHer backtest/hyperopt otomatik eklenir. Sonucu ve yorumu elle yaz.\n\n"
            "| Zaman (UTC) | Komut | Strateji | Dilim | Sonuç / not |\n|---|---|---|---|---|\n"
        )
    slice_name = "train" if args.command == "hyperopt" else args.slice
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    with EXPERIMENTS_LOG.open("a") as f:
        f.write(f"| {now} | {args.command} | {args.strategy} | {slice_name} | |\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safe Freqtrade wrapper for ft-lab")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("download", help="download 1h and 4h candles for all pairs")

    bt = sub.add_parser("backtest", help="backtest on one slice")
    bt.add_argument("--slice", choices=["train", "validation", "test"], required=True)
    bt.add_argument("--strategy", default=DEFAULT_STRATEGY)
    bt.add_argument("--final-test", action="store_true", help="required for --slice test")

    ho = sub.add_parser("hyperopt", help="parameter search, train slice only")
    ho.add_argument("--strategy", default=DEFAULT_STRATEGY)
    ho.add_argument("--epochs", type=int, default=200)
    ho.add_argument("--spaces", nargs="+", default=["buy", "sell"])

    parser.add_argument("--dry", action="store_true", help="print the command, don't run it")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cmd = build_command(args)
    print("$", " ".join(cmd))
    if args.dry:
        return 0
    log_run(args, cmd)
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    sys.exit(main())
