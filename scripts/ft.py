"""Safe wrapper around Freqtrade commands for ft-lab.

Why a wrapper: it takes dates ONLY from scripts/splits.py, always uses the
realistic fee, refuses to hyperopt on anything but the train slice, and logs
every run to docs/experiments.md so we can count how many times we tried.

    .venv/bin/python scripts/ft.py download
    .venv/bin/python scripts/ft.py backtest --slice train
    .venv/bin/python scripts/ft.py backtest --slice train --strategy TrendEma TrendEmaAtr
    .venv/bin/python scripts/ft.py backtest --slice train --strategy all
    .venv/bin/python scripts/ft.py benchmark --slice train
    .venv/bin/python scripts/ft.py report --slice train      # short comparison table
    .venv/bin/python scripts/ft.py backtest --slice validation
    .venv/bin/python scripts/ft.py backtest --slice test --final-test   # once per strategy!
    .venv/bin/python scripts/ft.py hyperopt --epochs 200 --spaces buy sell

    # robustness (Phase 3): other coins, double fee
    .venv/bin/python scripts/ft.py download --universe wide
    .venv/bin/python scripts/ft.py backtest --slice train --universe wide --strategy TrendEmaSlow
    .venv/bin/python scripts/ft.py backtest --slice train --fee-stress --strategy TrendEmaSlow
    .venv/bin/python scripts/ft.py report --slice train --universe wide
"""

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from splits import DATA_START, SLICES  # noqa: E402
from universe import UNIVERSES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
EXPERIMENTS_LOG = ROOT / "docs" / "experiments.md"
CONFIG = "/freqtrade/user_data/config/config.json"  # path inside the container
FEE = "0.0015"
STRESS_FEE = "0.003"  # 2x: does the rule survive much worse costs?
DEFAULT_STRATEGY = "TrendEma"
# Extra months before DATA_START so EMA200 has warm-up candles.
DOWNLOAD_FROM = f"{DATA_START.year - 1}1001"
# Freqtrade backtests one timeframe per run, so strategies are grouped by it.
# Default is 1h; list every strategy that uses something else here.
STRATEGY_TIMEFRAMES = {"TrendEma4h": "4h"}
ROUND1 = ["TrendEmaAtr", "TrendEmaAtrTrail", "TrendBreakout", "TrendEma4h"]
ROUND2 = ["TrendEmaAtrWide", "TrendEmaSlow", "TrendEmaMulti", "TrendEmaBtc"]
SLOW_SENSITIVITY = ["SlowFast40", "SlowFast60", "SlowSlow150", "SlowSlow250", "SlowTrend450", "SlowTrend750"]
ALL_STRATEGIES = ["TrendEma", *ROUND1, *ROUND2]


def docker_cmd(*args: str) -> list[str]:
    return ["docker", "compose", "run", "--rm", "freqtrade", *args]


def timeframe_of(strategy: str) -> str:
    return STRATEGY_TIMEFRAMES.get(strategy, "1h")


def pairs_args(args: argparse.Namespace) -> list[str]:
    """Extra --pairs for a non-default universe; empty = pairs from config.json."""
    pairs = UNIVERSES[getattr(args, "universe", "core")]
    return ["--pairs", *pairs] if pairs else []


def fee_of(args: argparse.Namespace) -> str:
    return STRESS_FEE if getattr(args, "fee_stress", False) else FEE


def build_commands(args: argparse.Namespace) -> list[list[str]]:
    """One or more docker commands to run, in order."""
    if args.command == "download":
        return [docker_cmd(
            "download-data", "--config", CONFIG,
            "--timerange", f"{DOWNLOAD_FROM}-",
            "--timeframes", "1h", "4h",
            *pairs_args(args),
        )]  # fmt: skip

    if args.command == "backtest":
        if args.slice == "test" and not args.final_test:
            raise SystemExit(
                "Refusing: the test slice is the final exam. Use it ONCE per strategy, "
                "after train and validation are done, and add --final-test."
            )
        strategies_wanted = ALL_STRATEGIES if args.strategy == ["all"] else args.strategy
        groups: dict[str, list[str]] = {}
        for strategy in strategies_wanted:
            groups.setdefault(timeframe_of(strategy), []).append(strategy)
        return [
            docker_cmd(
                "backtesting", "--config", CONFIG,
                "--strategy-list", *strategies,
                "--timeframe", timeframe,
                "--timerange", SLICES[args.slice].timerange,
                "--fee", fee_of(args),
                "--enable-protections",  # include our risk brakes in the simulation
                "--export", "trades",
                *pairs_args(args),
            )
            for timeframe, strategies in groups.items()
        ]  # fmt: skip

    if args.command in ("benchmark", "report"):
        # Runs our script inside the Freqtrade container, which already has
        # pandas and freqtrade, so no local Python setup is needed.
        extra = ["--timeframe", "1h"] if args.command == "benchmark" else []
        extra += ["--universe", args.universe, "--fee", fee_of(args)]
        return [[
            "docker", "compose", "run", "--rm",
            "-v", f"{ROOT / 'scripts'}:/freqtrade/scripts:ro",
            "--entrypoint", "python",
            "freqtrade", f"/freqtrade/scripts/{args.command}.py",
            "--slice", args.slice, *extra,
        ]]  # fmt: skip

    if args.command == "hyperopt":
        # Hyperopt only ever sees the train slice. There is no option to change it.
        return [docker_cmd(
            "hyperopt", "--config", CONFIG,
            "--strategy", args.strategy,
            "--timeframe", timeframe_of(args.strategy),
            "--timerange", SLICES["train"].timerange,
            "--fee", FEE,
            "--enable-protections",
            "--hyperopt-loss", "CalmarHyperOptLoss",
            "--epochs", str(args.epochs),
            "--spaces", *args.spaces,
        )]  # fmt: skip

    raise SystemExit(f"unknown command {args.command}")


def log_run(args: argparse.Namespace) -> None:
    if args.command in ("download", "benchmark", "report"):
        return
    if not EXPERIMENTS_LOG.exists():
        EXPERIMENTS_LOG.write_text(
            "# Deneme kaydı\n\nHer backtest/hyperopt otomatik eklenir. Sonucu ve yorumu elle yaz.\n\n"
            "| Zaman (UTC) | Komut | Strateji | Dilim | Sonuç / not |\n|---|---|---|---|---|\n"
        )
    slice_name = "train" if args.command == "hyperopt" else args.slice
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    with EXPERIMENTS_LOG.open("a") as f:
        strategies = args.strategy if isinstance(args.strategy, list) else [args.strategy]
        if strategies == ["all"]:
            strategies = ALL_STRATEGIES
        for strategy in strategies:
            note = []
            if getattr(args, "universe", "core") != "core":
                note.append(f"universe {args.universe}")
            if getattr(args, "fee_stress", False):
                note.append(f"fee {STRESS_FEE}")
            f.write(f"| {now} | {args.command} | {strategy} | {slice_name} | {', '.join(note)} |\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safe Freqtrade wrapper for ft-lab")
    sub = parser.add_subparsers(dest="command", required=True)

    dl = sub.add_parser("download", help="download 1h and 4h candles for all pairs")
    dl.add_argument("--universe", choices=UNIVERSES, default="core")

    bt = sub.add_parser("backtest", help="backtest on one slice")
    bt.add_argument("--slice", choices=["train", "validation", "test"], required=True)
    bt.add_argument("--strategy", nargs="+", default=[DEFAULT_STRATEGY],
                    help="one or more strategies, compared side by side")
    bt.add_argument("--final-test", action="store_true", help="required for --slice test")
    bt.add_argument("--universe", choices=UNIVERSES, default="core", help="which coins (scripts/universe.py)")
    bt.add_argument("--fee-stress", action="store_true", help=f"fee {STRESS_FEE} instead of {FEE}")

    bm = sub.add_parser("benchmark", help="buy-and-hold on one slice (runs in Docker)")
    bm.add_argument("--slice", choices=["train", "validation", "test"], required=True)
    bm.add_argument("--universe", choices=UNIVERSES, default="core")
    bm.add_argument("--fee-stress", action="store_true")

    rp = sub.add_parser("report", help="short table: all strategies vs buy-and-hold")
    rp.add_argument("--slice", choices=["train", "validation", "test"], required=True)
    rp.add_argument("--universe", choices=UNIVERSES, default="core")
    rp.add_argument("--fee-stress", action="store_true")

    ho = sub.add_parser("hyperopt", help="parameter search, train slice only")
    ho.add_argument("--strategy", default=DEFAULT_STRATEGY)
    ho.add_argument("--epochs", type=int, default=200)
    ho.add_argument("--spaces", nargs="+", default=["buy", "sell"])

    parser.add_argument("--dry", action="store_true", help="print the command, don't run it")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    commands = build_commands(args)
    for cmd in commands:
        print("$", " ".join(cmd))
    if args.dry:
        return 0
    log_run(args)
    for cmd in commands:
        code = subprocess.call(cmd, cwd=ROOT)
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    sys.exit(main())
