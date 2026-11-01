"""Safe wrapper around Freqtrade commands for ft-lab.

Why a wrapper: it takes dates ONLY from scripts/splits.py, always uses the
realistic fee, refuses to hyperopt on anything but the train slice, and logs
every run to docs/experiments.md so we can count how many times we tried.

    python3 scripts/ft.py download
    python3 scripts/ft.py backtest --slice train
    python3 scripts/ft.py backtest --slice train --strategy TrendEma TrendEmaAtr
    python3 scripts/ft.py backtest --slice train --strategy all
    python3 scripts/ft.py benchmark --slice train
    python3 scripts/ft.py report --slice train      # short comparison table
    python3 scripts/ft.py backtest --slice validation
    python3 scripts/ft.py backtest --slice test --final-test   # once per strategy!
    python3 scripts/ft.py hyperopt --epochs 200 --spaces buy sell

    # robustness (Phase 3): other coins, double fee
    python3 scripts/ft.py download --universe wide
    python3 scripts/ft.py backtest --slice train --universe wide --strategy TrendEmaSlow
    python3 scripts/ft.py backtest --slice train --fee-stress --strategy TrendEmaSlow
    python3 scripts/ft.py report --slice train --universe wide
    python3 scripts/ft.py backtest --slice train --no-kill-switch --strategy all
    python3 scripts/ft.py report --slice train --no-kill-switch
"""

import argparse
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from splits import DATA_START, RESTRICTED_SLICES, SLICES  # noqa: E402
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
EARLY_FROM = "20170801"  # for --early: warm-up months before the 2018 'early' slice
# Freqtrade backtests one timeframe per run, so strategies are grouped by it.
# Default is 1h; list every strategy that uses something else here.
STRATEGY_TIMEFRAMES = {
    "TrendEma4h": "4h",
    "DipRsi4h": "4h",
    "NostalgiaForInfinityX8": "5m",
    "TrendSmaDaily": "1d",
    "TrendDonchianEnsemble": "1d",
    "TrendDonchianEnsembleFull": "1d",
    "TrendEmaBtcRisingGap4h": "4h",
    "TrendEmaVolTarget2h": "2h",
    "TrendEmaVolTargetDaily": "1d",
}
ROUND1 = ["TrendEmaAtr", "TrendEmaAtrTrail", "TrendBreakout", "TrendEma4h"]
ROUND2 = ["TrendEmaAtrWide", "TrendEmaSlow", "TrendEmaMulti", "TrendEmaBtc"]
ROUND3 = ["TrendEmaAdx", "TrendEmaLongTrend"]
ROUND4 = ["TrendDonchianEnsemble", "TrendDonchianEnsembleFull"]
ROUND5 = ["TrendEmaHold"]
ROUND6 = ["DipRsi", "DipRsi4h"]  # Phase 2: buy dips (mean reversion)
ROUND7 = ["TrendEmaExitConfirm", "TrendEmaSlope", "TrendEmaEntryConfirm"]
ROUND8 = ["TrendEmaPyramid"]  # add to winners once, total risk still 1%
ROUND9 = ["TrendEmaPyramidBtc"]  # add only while BTC > EMA200
ROUND10 = ["TrendSmaDaily"]  # after the final test: daily close vs 200-day SMA (Faber 2007)  # whipsaw fixes from the trade analysis
EMA_SENSITIVITY = ["EmaFast15", "EmaFast25", "EmaSlow40", "EmaSlow60", "EmaTrend150", "EmaTrend250"]
PYRAMID_SENSITIVITY = ["Pyramid3", "Pyramid6"]
ENTRY_CONFIRM_SENSITIVITY = ["EntryConfirm2", "EntryConfirm4"]
SLOW_SENSITIVITY = ["SlowFast40", "SlowFast60", "SlowSlow150", "SlowSlow250", "SlowTrend450", "SlowTrend750"]
# Famous third-party bots, run ONLY as research benchmarks next to our rule.
# Their code lives in user_data/strategies/thirdparty (not loadable by the bot).
THIRD_PARTY = ["NostalgiaForInfinityX8"]
THIRD_PARTY_PATH = "/freqtrade/user_data/strategies/thirdparty"
BOTS_CONFIG = "/freqtrade/user_data/config/research-bots.json"
ALL_STRATEGIES = ["TrendEma", *ROUND1, *ROUND2, *ROUND3, *ROUND4, *ROUND5, *ROUND6, *ROUND7, *ROUND8, *ROUND9, *ROUND10]


DRILL_TIMERANGE = "20291215-20300601"  # scripts/drill.py TIMERANGE (made-up data in 2029-2030)
DRILL_RESULTS = "user_data/backtest_results/drill"
DRILL_PAIRS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]
TEST_IMAGE = "ft-lab-test"  # freqtrade:2026.10 + pytest, built from tests/Dockerfile


def docker_cmd(*args: str) -> list[str]:
    return ["docker", "compose", "run", "--rm", "freqtrade", *args]


def timeframe_of(strategy: str) -> str:
    return STRATEGY_TIMEFRAMES.get(strategy, "1h")


def scan_from(today: date | None = None) -> str:
    """Download start for `scan`: 120 days before today (UTC)."""
    today = today or datetime.now(timezone.utc).date()
    return (today - timedelta(days=120)).strftime("%Y%m%d")


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
    sl = getattr(args, "slice", None)
    if sl in RESTRICTED_SLICES and getattr(args, "universe", "core") not in RESTRICTED_SLICES[sl]:
        raise SystemExit(f"Refusing: {sl} is a reserved/restricted slice, allowed only with --universe "
                         f"{' or '.join(RESTRICTED_SLICES[sl])} (window24 reuses old dates; judge slices are one-look judges).")
    if args.command == "test":
        # The Mac's python3 has no pandas/freqtrade: tests run in the test image (tests/Dockerfile).
        build = [["docker", "build", "-q", "-t", TEST_IMAGE, str(ROOT / "tests")]] if args.build else []
        return [*build, ["docker", "run", "--rm", "--entrypoint", "python", "-v", f"{ROOT}:/repo", "-w", "/repo",
                         TEST_IMAGE, "-m", "pytest", "-q", *args.pytest_args]]  # fmt: skip

    if args.command == "drill":
        # Kill-switch drill on made-up data (scripts/drill.py): kill switch ON (no research flag).
        py = ["docker", "compose", "run", "--rm", "-v", f"{ROOT / 'scripts'}:/freqtrade/scripts:ro",
              "-v", f"{ROOT / 'minibot'}:/freqtrade/minibot:ro", "--entrypoint", "python", "freqtrade",
              "/freqtrade/scripts/drill.py"]  # fmt: skip
        return [
            [*py, "generate"],
            docker_cmd("backtesting", "--config", CONFIG, "--strategy", "TrendEmaVolTarget", "--timeframe", "1h",
                       "--timerange", DRILL_TIMERANGE, "--fee", FEE, "--enable-protections", "--export", "trades",
                       "--datadir", "/freqtrade/user_data/data/drill",
                       "--backtest-directory", f"/freqtrade/{DRILL_RESULTS}",
                       "--pairs", *DRILL_PAIRS),  # fmt: skip
            [*py, "compare"],
        ]

    if args.command == "replay":
        return [["docker", "compose", "run", "--rm",
                 "-v", f"{ROOT / 'scripts'}:/freqtrade/scripts:ro", "-v", f"{ROOT / 'minibot'}:/freqtrade/minibot:ro",
                 "--entrypoint", "python", "freqtrade", "/freqtrade/scripts/replay.py", "--slice", args.slice]]  # fmt: skip

    if args.command == "deflated":
        import trials  # stdlib; docs/ is not mounted in the container, so N is read here on the host

        n = trials.n_trials(trials.load())
        return [["docker", "compose", "run", "--rm", "-v", f"{ROOT / 'scripts'}:/freqtrade/scripts:ro",
                 "--entrypoint", "python", "freqtrade", "/freqtrade/scripts/deflated.py", str(n), *args.strategy]]  # fmt: skip

    if args.command == "minibot":
        # Paper trading only (public prices, no keys); the state file minibot/state.json is written in the repo.
        # --demo: docker passes .env to the container (FTLAB_DEMO_KEY/SECRET); ft.py itself never reads it.
        env = ["--env-file", str(ROOT / ".env")] if args.demo else []
        return [["docker", "run", "--rm", *env, "--entrypoint", "python", "-v", f"{ROOT}:/repo", "-w", "/repo", TEST_IMAGE,
                 "-m", "minibot.bot", *(["--once"] if args.once else []), "--rule", args.rule,
                 *(["--demo"] if args.demo else [])]]  # fmt: skip

    if args.command == "download":
        return [
            docker_cmd(
                "download-data", "--config", CONFIG,
                "--timerange", f"{EARLY_FROM if getattr(args, 'early', False) else DOWNLOAD_FROM}-",
                "--timeframes", "1h", "2h", "4h", "1d",
                *(["--prepend"] if getattr(args, "early", False) else []),
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
                "--timerange", f"{EARLY_FROM if getattr(args, 'early', False) else DAILY_FROM}-",
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

    if args.command == "chart":
        pair = args.pair.upper() if "/" in args.pair else f"{args.pair.upper()}/USDT"
        return [
            # fresh candles for this one coin (1h for our bot's view, 1d for the chart)
            docker_cmd("download-data", "--config", CONFIG, "--timerange", f"{DAILY_FROM}-",
                       "--timeframes", "1h", "1d", "--pairs", pair),
            [
                "docker", "compose", "run", "--rm",
                "-v", f"{ROOT / 'scripts'}:/freqtrade/scripts:ro",
                "--entrypoint", "python",
                "freqtrade", "/freqtrade/scripts/chart.py", "--pair", pair,
                *(["--lang", "tr"] if getattr(args, "tr", False) else []),
            ],
        ]  # fmt: skip

    if args.command == "ai-score":
        return [[
            "docker", "compose", "run", "--rm",
            "-v", f"{ROOT / 'scripts'}:/freqtrade/scripts:ro",
            "-v", f"{ROOT / 'docs' / 'fresh'}:/freqtrade/fresh",  # reads ai-views.md, writes ai-scores.csv
            "--entrypoint", "python",
            "freqtrade", "/freqtrade/scripts/ai_score.py",
        ]]  # fmt: skip

    if args.command == "explain":
        return [[
            "docker", "compose", "run", "--rm",
            "-v", f"{ROOT / 'scripts'}:/freqtrade/scripts:ro",
            "--entrypoint", "python",
            "freqtrade", "/freqtrade/scripts/explain.py",
        ]]  # fmt: skip

    if args.command == "judge-eval":  # read-only: existing results over the full slice window
        return [["docker", "compose", "run", "--rm", "-v", f"{ROOT / 'scripts'}:/freqtrade/scripts:ro",
                 "--entrypoint", "python", "freqtrade", "/freqtrade/scripts/judge_eval.py",
                 "--slice", args.slice, "--universe", args.universe,
                 *(["--results-dir", f"/freqtrade/{NO_KILL_DIR}"] if args.no_kill_switch else []),
                 "--strategy", *args.strategy]]  # fmt: skip

    if args.command == "durations":  # read-only: existing backtest results
        return [["docker", "compose", "run", "--rm", "-v", f"{ROOT / 'scripts'}:/freqtrade/scripts:ro",
                 "--entrypoint", "python", "freqtrade", "/freqtrade/scripts/durations.py",
                 "--slice", args.slice, "--universe", args.universe,
                 *(["--results-dir", f"/freqtrade/{NO_KILL_DIR}"] if args.no_kill_switch else []),
                 "--strategy", *args.strategy]]  # fmt: skip

    if args.command == "postmortem":  # final test slice, analysis only (scripts/postmortem.py)
        return [["docker", "compose", "run", "--rm", "-v", f"{ROOT / 'scripts'}:/freqtrade/scripts:ro",
                 "--entrypoint", "python", "freqtrade", "/freqtrade/scripts/postmortem.py"]]  # fmt: skip

    if args.command == "forward-risk":
        return [["docker", "compose", "run", "--rm", "-v", f"{ROOT / 'scripts'}:/freqtrade/scripts:ro",
                 "--entrypoint", "python", "freqtrade", "/freqtrade/scripts/forward_risk.py"]]  # fmt: skip

    if args.command == "expected":
        return [[
            "docker", "compose", "run", "--rm",
            "-v", f"{ROOT / 'scripts'}:/freqtrade/scripts:ro",
            "--entrypoint", "python",
            "freqtrade", "/freqtrade/scripts/expected.py",
        ]]  # fmt: skip

    if args.command == "execution":
        return [[
            "docker", "compose", "run", "--rm",
            "-v", f"{ROOT / 'scripts'}:/freqtrade/scripts:ro",
            "-v", f"{ROOT / 'minibot'}:/freqtrade/minibot:ro",  # demo fills: minibot/state.demo.json
            "--entrypoint", "python",
            "freqtrade", "/freqtrade/scripts/execution.py",
        ]]  # fmt: skip

    if args.command == "scan":
        return [
            # fresh 1h candles for every coin of the group (incremental, no --erase). Start 120 days
            # back: enough for EMA200 + 30-day volatility, and no "--prepend" warnings for coins
            # whose stored history starts later than 2019
            docker_cmd("download-data", "--config", CONFIG, "--timerange", f"{scan_from()}-",
                       "--timeframes", "1h", *pairs_args(args)),
            [
                "docker", "compose", "run", "--rm",
                "-v", f"{ROOT / 'scripts'}:/freqtrade/scripts:ro",
                "--entrypoint", "python",
                "freqtrade", "/freqtrade/scripts/scan.py", "--universe", args.universe,
                *(["--csv"] if getattr(args, "csv", False) else []),
            ],
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

    if args.command == "regimes":
        return [[
            "docker", "compose", "run", "--rm",
            "-v", f"{ROOT / 'scripts'}:/freqtrade/scripts:ro",
            "--entrypoint", "python",
            "freqtrade", "/freqtrade/scripts/regimes.py",
            "--slice", args.slice, "--universe", args.universe,
            *(["--results-dir", f"/freqtrade/{NO_KILL_DIR}"] if args.no_kill_switch else []),
            "--strategy", *args.strategy,
        ]]  # fmt: skip

    if args.command == "bots":
        if args.slice == "test" and not args.final_test:
            raise SystemExit("Refusing: the test slice is the final exam. Add --final-test (once per strategy).")
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
    if args.command in ("download", "benchmark", "report", "montecarlo", "walkforward", "bots", "analyze", "chart", "scan",
                        "execution", "expected", "explain", "ai-score", "regimes", "test", "minibot", "deflated", "replay", "drill", "forward-risk", "postmortem", "durations", "judge-eval"):  # fmt: skip
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
    dl.add_argument("--early", action="store_true", help="also candles from 2017-08 (for the 'early' 2018-2020 slice)")

    te = sub.add_parser("test", help="run the test suite in Docker (the Mac's python3 has no pandas/freqtrade)")
    te.add_argument("--build", action="store_true", help="(re)build the test image from tests/Dockerfile first")
    te.add_argument("pytest_args", nargs="*", help="extra pytest arguments, e.g. tests/test_minibot.py")

    sub.add_parser("drill", help="kill-switch drill: made-up crash through Freqtrade (kill switch ON) and the mini bot")

    rp = sub.add_parser("replay", help="minibot demo loop over stored candles vs the Freqtrade backtest (no keys)")
    rp.add_argument("--slice", choices=["fresh", "validation"], required=True)

    df = sub.add_parser("deflated", help="Deflated Sharpe Ratio of VolTarget/TrendEma; N = trials in docs/trials.csv")
    df.add_argument("--strategy", nargs="+", default=[], help="extra strategies to score next to the defaults")

    mb = sub.add_parser("minibot", help="the from-scratch paper bot (Phase 4), in Docker")
    mb.add_argument("--once", action="store_true", help="one pass, then exit")
    mb.add_argument("--rule", choices=["voltarget", "trendema"], default="voltarget")
    mb.add_argument("--demo", action="store_true", help="Binance Demo Mode (needs demo keys in .env; Kaan's approval)")

    ch = sub.add_parser("chart", help="chart reading of one coin in numbers (downloads it first)")
    ch.add_argument("--pair", required=True, help="e.g. ETH/USDT or just ETH")
    ch.add_argument("--tr", action="store_true", help="simple Turkish sentences (for Kaan)")

    sub.add_parser("ai-score", help="score the AI chart views after 7 days (docs/fresh/ai-scores.csv)")
    sub.add_parser("explain", help="every dry-run trade explained in plain Turkish (read-only)")
    je = sub.add_parser("judge-eval", help="strategy results over the full slice window (read-only)")
    je.add_argument("--slice", choices=["train", "validation", "fresh", "early", "window24", "judge21", "judge25"], required=True)
    je.add_argument("--universe", choices=UNIVERSES, default="core")
    je.add_argument("--no-kill-switch", action="store_true")
    je.add_argument("--strategy", nargs="+", required=True)
    du = sub.add_parser("durations", help="trade duration vs P/L and fees from existing results (read-only)")
    du.add_argument("--slice", choices=["train", "validation", "fresh", "early", "window24", "judge21", "judge25"], required=True)
    du.add_argument("--universe", choices=UNIVERSES, default="core")
    du.add_argument("--no-kill-switch", action="store_true")
    du.add_argument("--strategy", nargs="+", default=["TrendEmaVolTarget"])
    sub.add_parser("postmortem", help="final test slice month by month (analysis only, used-up slice)")
    sub.add_parser("forward-risk", help="12-month forward risk with the latching kill switch (block bootstrap, judging only)")
    sub.add_parser("expected", help="is VolTarget's fresh result inside its expected range? (judging only)")
    sub.add_parser("execution", help="read-only fill/slippage/fee report from the dry-run DB(s)")

    sc = sub.add_parser("scan", help="what our rule sees on many coins right now (downloads 1h first)")
    sc.add_argument("--universe", choices=UNIVERSES, default="pool")
    sc.add_argument("--csv", action="store_true", help="also print a breadth_csv line (daily.py records it)")

    bt = sub.add_parser("backtest", help="backtest on one slice")
    bt.add_argument("--slice", choices=["train", "validation", "test", "fresh", "early", "window24", "judge21", "judge25"], required=True)
    bt.add_argument("--strategy", nargs="+", default=[DEFAULT_STRATEGY],
                    help="one or more strategies, compared side by side")
    bt.add_argument("--final-test", action="store_true", help="required for --slice test")
    bt.add_argument("--universe", choices=UNIVERSES, default="core", help="which coins (scripts/universe.py)")
    bt.add_argument("--fee-stress", action="store_true", help=f"fee {STRESS_FEE} instead of {FEE}")
    bt.add_argument("--no-kill-switch", action="store_true",
                    help="research only: judge the rule over the whole slice (never affects the bot)")

    bm = sub.add_parser("benchmark", help="buy-and-hold on one slice (runs in Docker)")
    bm.add_argument("--slice", choices=["train", "validation", "test", "fresh", "early", "window24", "judge21", "judge25"], required=True)
    bm.add_argument("--universe", choices=UNIVERSES, default="core")
    bm.add_argument("--fee-stress", action="store_true")

    rp = sub.add_parser("report", help="short table: all strategies vs buy-and-hold")
    rp.add_argument("--slice", choices=["train", "validation", "test", "fresh", "early", "window24", "judge21", "judge25"], required=True)
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
    bo.add_argument("--slice", choices=["train", "validation", "test", "fresh", "early", "window24", "judge21", "judge25"], required=True)
    bo.add_argument("--final-test", action="store_true", help="required for --slice test (final exam)")
    bo.add_argument("--universe", choices=UNIVERSES, default="core")
    bo.add_argument("--fee-stress", action="store_true")
    bo.add_argument("--no-kill-switch", action="store_true")
    bo.add_argument("--strategy", nargs="+", default=[DEFAULT_STRATEGY, *THIRD_PARTY])

    rg = sub.add_parser("regimes", help="bot results split by BTC market regime (train/early only, analysis)")
    rg.add_argument("--slice", choices=["train", "early"], required=True)
    rg.add_argument("--universe", choices=UNIVERSES, default="core")
    rg.add_argument("--no-kill-switch", action="store_true")
    rg.add_argument("--strategy", nargs="+", default=["TrendEma", "TrendEmaVolTarget"])

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
        print("$", " ".join(cmd), flush=True)
    if args.dry:
        return 0
    log_run(args)
    if getattr(args, "no_kill_switch", False):
        (ROOT / NO_KILL_DIR).mkdir(parents=True, exist_ok=True)
    if args.command == "drill":
        (ROOT / DRILL_RESULTS).mkdir(parents=True, exist_ok=True)
    for cmd in commands:
        code = subprocess.call(cmd, cwd=ROOT)
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    sys.exit(main())
