"""One command for the daily forward check on the "fresh" slice.

    python3 scripts/daily.py            # download new candles, backtest, write the report
    python3 scripts/daily.py --no-download

What it does, in order:
  1. ft.py download (core + wide): adds only the candles since the last run.
  2. ft.py backtest --slice fresh for every candidate, core and wide (kill switch ON, as live).
  3. ft.py bots --slice fresh: the famous bot types next to our candidates.
  4. Saves everything to docs/fresh/YYYY-MM-DD.md, so the days can be compared.

The fresh slice is for JUDGING only. Rules are never changed because of what it
shows (docs/journal.md); new ideas come from the train slice.
Stdlib only: it only calls scripts/ft.py, like a human would.
"""

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FT = [sys.executable, str(ROOT / "scripts" / "ft.py")]
OUT_DIR = ROOT / "docs" / "fresh"

# The strategy the dry-run bot runs + the current candidate(s). NFI runs on 5m
# candles and takes much longer, so it is opt-in (--with-nfi).
CANDIDATES = ["TrendEma", "TrendEmaBtcRising", "TrendEmaBtcRisingGap", "TrendEmaVolTarget"]
UNIVERSES = ["core", "wide", "alt2022", "alt2023", "alt2024"]


def run(args: list[str], capture: bool = False) -> tuple[int, str]:
    r = subprocess.run([*FT, *args], cwd=ROOT, capture_output=capture, text=True)
    return r.returncode, (r.stdout or "") if capture else ""


def table_lines(text: str) -> str:
    """Keep the result lines, drop docker noise."""
    keep = [line for line in text.splitlines() if not line.startswith(("$ docker", " Container"))]
    return "\n".join(keep).strip()


def plan(with_nfi: bool, download: bool) -> list[tuple[str, list[str], bool]]:
    """(title, ft.py arguments, capture output for the report?) in run order."""
    steps: list[tuple[str, list[str], bool]] = []
    if download:
        steps += [("download core", ["download"], False), ("download wide", ["download", "--universe", "wide"], False)]
        if with_nfi:
            steps.append(("download 5m", ["download", "--fine"], False))
    for universe in UNIVERSES:
        extra = [] if universe == "core" else ["--universe", universe]
        steps.append((f"backtest {universe}", ["backtest", "--slice", "fresh", *extra, "--strategy", *CANDIDATES], False))
    if with_nfi:
        steps.append(("backtest NFI", ["backtest", "--slice", "fresh", "--strategy", "NostalgiaForInfinityX8"], False))
    shown = CANDIDATES + (["NostalgiaForInfinityX8"] if with_nfi else [])
    for universe in UNIVERSES:
        extra = [] if universe == "core" else ["--universe", universe]
        names = shown if universe == "core" else CANDIDATES
        steps.append((f"bots {universe}", ["bots", "--slice", "fresh", *extra, "--strategy", *names], True))
    return steps


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="daily forward check on the fresh slice")
    parser.add_argument("--no-download", action="store_true")
    parser.add_argument("--with-nfi", action="store_true", help="also run NFI X8 (5m, slow)")
    args = parser.parse_args(argv)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report = [f"# Taze veri kontrolü {today}", "",
              "Sadece yargı için. Kurallar bu sonuçlara bakılarak değiştirilmez (docs/journal.md).", ""]  # fmt: skip
    for title, ft_args, capture in plan(args.with_nfi, not args.no_download):
        print(f"== {title}: ft.py {' '.join(ft_args)}", flush=True)
        code, out = run(ft_args, capture)
        if code != 0:
            print(f"FAILED ({code}): {title}")
            return code
        if capture:
            print(out)
            report += [f"## {title}", "", "```", table_lines(out), "```", ""]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{today}.md"
    path.write_text("\n".join(report))
    print(f"report: {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
