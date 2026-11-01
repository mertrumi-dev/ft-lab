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
    .venv/bin/python scripts/ft.py backtest --slice train --no-kill-switch --strategy all
    .venv/bin/python scripts/ft.py report --slice train --no-kill-switch
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
RESEARCH_CONFIG = "/freqtrade/user_data/config/research-no-kill-switch.json"
# Separate folder so these results never mix with normal ones in the report.
NO_KILL_DIR = "user_data/backtest_results/no_kill_switch"
STRESS_FEE = "0.003"  # 2x: does the rule survive much worse costs?
DEFAULT_STRATEGY = "TrendEma"
# Extra months before DATA_START so EMA200 has warm-up candles.
DOWNLOAD_FROM = f"{DATA_START.year - 1}1001"
DAILY_FROM = f"{DATA_START.year - 2}0101"
# Freqtrade backtests one timeframe per run, so strategies are grouped by it.
# Default is 1h; list every strategy that uses something else here.
STRATEGY_TIMEFRAMES = {
    "TrendEma4h": "4h",
    "DipRsi4h": "4h",
    "NostalgiaForInfinityX8": "5m",
    "TrendDonchianEnsemble": "1d",
    "TrendDonchianEnsembleFull": "1d",
}
ROUND1 = ["TrendEmaAtr", "TrendEmaAtrTrail", "TrendBreakout", "TrendEma4h"]
ROUND2 = ["TrendEmaAtrWide", "TrendEmaSlow", "TrendEmaMulti", "TrendEmaBtc"]
ROUND3 = ["TrendEmaAdx", "TrendEmaLongTrend"]
ROUND4 = ["TrendDonchianEnsemble", "TrendDonchianEnsembleFull"]
ROUND5 = ["TrendEmaHold"]
ROUND6 = ["DipRsi", "DipRsi4h"]  # Phase 2: buy dips (mean reversion)
ROUND7 = ["TrendEmaExitConfirm", "TrendEmaSlope"]  # whipsaw fixes from the trade analysis
EMA_SENSITIVITY = ["EmaFast15", "EmaFast25", "EmaSlow40", "EmaSlow60", "EmaTrend150", "EmaTrend250"]
SLOW_SENSITIVITY = ["SlowFast40", "SlowFast60", "SlowSlow150", "SlowSlow250", "SlowTrend450", "SlowTrend750"]
# Famous third-party bots, run ONLY as research benchmarks next to our rule.
# Their code lives in user_data/strategies/thirdparty (not loadable by the bot).
THIRD_PARTY = ["NostalgiaForInfinityX8"]
THIRD_PARTY_PATH = "/freqtrade/user_data/strategies/thirdparty"
BOTS_CONFIG = "/freqtrade/user_data/config/research-bots.json"
ALL_STRATEGIES = ["TrendEma", *ROUND1, *ROUND2, *ROUND3, *ROUND4, *ROUND5, *ROUND6, *ROUND7]


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


def kill_switch_args(args: argparse.Namespace) -> list[str]:
    if not getattr(args, "no_kill_switch", False):
        return []
    return ["--config", RESEARCH_CONFIG, "--backtest-directory", f"/freqtrade/{NO_KILL_DIR}"]


def third_party_args(strategies: list[str]) -> list[str]:
    """Where the benchmark bots live, and their research config (5 open trades, dry-run)."""
    if not any(s in THIRD_PARTY for s in strategies):
        return []
    return ["--strategy-path", THIRD_PARTY_PATH, "--config", BOTS_CONFIG]


def build_commands(args: argparse.Namespace) -> list[list[str]]:
    """One or more docker commands to run, in order."""
    if args.command == "download":
        return [
            docker_cmd(
                "download-data", "--config", CONFIG,
                "--timerange", f"{DOWNLOAD_FROM}-",
                "--timeframes", "1h", "4h",
                *pairs_args(args),
            ),
            *([docker_cmd(
                # 5m/15m candles: only needed by the NFI benchmark bot (it trades on 5m)
                "download-data", "--config", CONFIG,
                "--timerange", f"{DOWNLOAD_FROM}-",
                "--timeframes", "5m", "15m",
                *pairs_args(args),
            )] if getattr(args, "fine", False) else []),
            # daily strategies look back up to a year, so daily candles start 2 years early
            docker_cmd(
                "download-data", "--config", CONFIG,
                "--timerange", f"{DAILY_FROM}-",
                "--timeframes", "1d",
                "--erase",  # daily files are small; re-download whole history so it starts in 2019
                *pairs_args(args),
            ),
        ]  # fmt: skip

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
                *third_party_args(strategies),
                *kill_switch_args(args),
                *pairs_args(args),  # last: --pairs takes every word after it
            )
            for timeframe, strategies in groups.items()
        ]  # fmt: skip

    if args.command == "montecarlo":
        return [[
            "docker", "compose", "run", "--rm",
            "-v", f"{ROOT / 'scripts'}:/freqtrade/scripts:ro",
            "--entrypoint", "python",
            "freqtrade", "/freqtrade/scripts/montecarlo.py",
            "--slice", args.slice, "--universe", args.universe,
            *(["--results-dir", f"/freqtrade/{NO_KILL_DIR}"] if args.no_kill_switch else []),
            "--strategy", *args.strategy,
        ]]  # fmt: skip

    if args.command == "analyze":
        return [[
            "docker", "compose", "run", "--rm",
            "-v", f"{ROOT / 'scripts'}:/freqtrade/scripts:ro",
            "--entrypoint", "python",
            "freqtrade", "/freqtrade/scripts/analyze.py",
            "--slice", args.slice, "--universe", args.universe,
            *(["--results-dir", f"/freqtrade/{NO_KILL_DIR}"] if args.no_kill_switch else []),
            "--strategy", *args.strategy,
        ]]  # fmt: skip

    if args.command == "bots":
        return [[
            "docker", "compose", "run", "--rm",
            "-v", f"{ROOT / 'scripts'}:/freqtrade/scripts:ro",
            "--entrypoint", "python",
            "freqtrade", "/freqtrade/scripts/bots.py",
            "--slice", args.slice, "--universe", args.universe, "--fee", fee_of(args),
            *(["--results-dir", f"/freqtrade/{NO_KILL_DIR}"] if args.no_kill_switch else []),
            "--strategy", *args.strategy,
        ]]  # fmt: skip

    if args.command == "walkforward":
        return [[
            "docker", "compose", "run", "--rm",
            "-v", f"{ROOT / 'scripts'}:/freqtrade/scripts:ro",
            "--entrypoint", "python",
            "freqtrade", "/freqtrade/scripts/walkforward.py",
            "--slice", args.slice, "--universe", args.universe, "--fixed", args.fixed,
            *(["--results-dir", f"/freqtrade/{NO_KILL_DIR}"] if args.no_kill_switch else []),
            "--strategy", *args.strategy,
        ]]  # fmt: skip

    if args.command in ("benchmark", "report"):
        # Runs our script inside the Freqtrade container, which already has
        # pandas and freqtrade, so no local Python setup is needed.
        extra = ["--timeframe", "1h"] if args.command == "benchmark" else []
        extra += ["--universe", args.universe, "--fee", fee_of(args)]
        if args.command == "report" and args.no_kill_switch:
            extra += ["--results-dir", f"/freqtrade/{NO_KILL_DIR}"]
        if args.command == "report" and args.by_year:
            extra += ["--by-year"]
        if args.command == "report" and args.strategy:
            extra += ["--strategy", *args.strategy]
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
    if args.command in ("download", "benchmark", "report", "montecarlo", "walkforward", "bots", "analyze"):
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
            if getattr(args, "no_kill_switch", False):
                note.append("no kill switch (research)")
            f.write(f"| {now} | {args.command} | {strategy} | {slice_name} | {', '.join(note)} |\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safe Freqtrade wrapper for ft-lab")
    sub = parser.add_subparsers(dest="command", required=True)

    dl = sub.add_parser("download", help="download 1h, 4h and 1d candles for all pairs")
    dl.add_argument("--universe", choices=UNIVERSES, default="core")
    dl.add_argument("--fine", action="store_true", help="also 5m and 15m (for the NFI benchmark bot)")

    bt = sub.add_parser("backtest", help="backtest on one slice")
    bt.add_argument("--slice", choices=["train", "validation", "test"], required=True)
    bt.add_argument("--strategy", nargs="+", default=[DEFAULT_STRATEGY],
                    help="one or more strategies, compared side by side")
    bt.add_argument("--final-test", action="store_true", help="required for --slice test")
    bt.add_argument("--universe", choices=UNIVERSES, default="core", help="which coins (scripts/universe.py)")
    bt.add_argument("--fee-stress", action="store_true", help=f"fee {STRESS_FEE} instead of {FEE}")
    bt.add_argument("--no-kill-switch", action="store_true",
                    help="research only: judge the rule over the whole slice (never affects the bot)")

    bm = sub.add_parser("benchmark", help="buy-and-hold on one slice (runs in Docker)")
    bm.add_argument("--slice", choices=["train", "validation", "test"], required=True)
    bm.add_argument("--universe", choices=UNIVERSES, default="core")
    bm.add_argument("--fee-stress", action="store_true")

    rp = sub.add_parser("report", help="short table: all strategies vs buy-and-hold")
    rp.add_argument("--slice", choices=["train", "validation", "test"], required=True)
    rp.add_argument("--universe", choices=UNIVERSES, default="core")
    rp.add_argument("--fee-stress", action="store_true")
    rp.add_argument("--no-kill-switch", action="store_true", help="show the no-kill-switch research runs")
    rp.add_argument("--by-year", action="store_true", help="also show each calendar year separately")
    rp.add_argument("--strategy", nargs="+", help="only these strategies")

    mc = sub.add_parser("montecarlo", help="reshuffle trades 2000x: how bad could it get")
    mc.add_argument("--slice", choices=["train", "validation"], required=True)
    mc.add_argument("--strategy", nargs="+", default=[DEFAULT_STRATEGY])
    mc.add_argument("--universe", choices=UNIVERSES, default="core")
    mc.add_argument("--no-kill-switch", action="store_true")

    an = sub.add_parser("analyze", help="split trades by exit reason, coin, holding time, year (train only)")
    an.add_argument("--slice", choices=["train"], required=True)
    an.add_argument("--strategy", nargs="+", default=[DEFAULT_STRATEGY])
    an.add_argument("--universe", choices=UNIVERSES, default="core")
    an.add_argument("--no-kill-switch", action="store_true")

    bo = sub.add_parser("bots", help="famous bot types (DCA, grid, 3Commas DCA, NFI) vs our rule")
    bo.add_argument("--slice", choices=["train", "validation"], required=True)
    bo.add_argument("--universe", choices=UNIVERSES, default="core")
    bo.add_argument("--fee-stress", action="store_true")
    bo.add_argument("--no-kill-switch", action="store_true")
    bo.add_argument("--strategy", nargs="+", default=[DEFAULT_STRATEGY, *THIRD_PARTY])

    wf = sub.add_parser("walkforward", help="pick best on past 12 months, trade next 6 (train only)")
    wf.add_argument("--slice", choices=["train"], required=True)
    wf.add_argument("--strategy", nargs="+", default=["TrendEma", *EMA_SENSITIVITY])
    wf.add_argument("--fixed", default=DEFAULT_STRATEGY)
    wf.add_argument("--universe", choices=UNIVERSES, default="core")
    wf.add_argument("--no-kill-switch", action="store_true")

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
    if getattr(args, "no_kill_switch", False):
        (ROOT / NO_KILL_DIR).mkdir(parents=True, exist_ok=True)
    for cmd in commands:
        code = subprocess.call(cmd, cwd=ROOT)
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    sys.exit(main())
