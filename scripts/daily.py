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
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health  # noqa: E402
import kaan_report  # noqa: E402
import prereg  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FT = [sys.executable, str(ROOT / "scripts" / "ft.py")]
OUT_DIR = ROOT / "docs" / "fresh"
BREADTH_CSV = OUT_DIR / "breadth.csv"
BREADTH_HEADER = "date,n_coins,breadth,n_in_trend,n_entry_now,BTC,ETH,SOL,BNB,XRP"

# The strategy the dry-run bot runs + the current candidate(s). NFI runs on 5m
# candles and takes much longer, so it is opt-in (--with-nfi).
CANDIDATES = ["TrendEma", "TrendEmaBtcRising", "TrendEmaBtcRisingGap", "TrendEmaVolTarget", "TrendEmaVolTargetAdx"]
UNIVERSES = ["core", "wide", "alt2022", "alt2023", "alt2024"]
# "Watch" rows: rules that FAILED their pre-registered tests but looked good on validation.
# Tracked forward for judging only; never tuned on fresh (docs/journal.md 2026-11-01).
WATCH = ["TrendEmaVolTarget2h"]
WATCH_UNIVERSES = {"core_gold": ["TrendEmaVolTarget"]}


CHART_COINS = ["BTC", "ETH", "SOL", "BNB", "XRP"]


def run(args: list[str], capture: bool = False) -> tuple[int, str]:
    r = subprocess.run([*FT, *args], cwd=ROOT, capture_output=capture, text=True)
    return r.returncode, (r.stdout or "") if capture else ""


def table_lines(text: str) -> str:
    """Keep the result lines, drop docker noise."""
    keep = [line for line in text.splitlines() if not line.startswith(("$ docker", " Container"))]
    return "\n".join(keep).strip()


def health_summary() -> dict:
    """Bot health numbers for the short report (read-only, same functions as health.py)."""
    try:
        now = datetime.now(timezone.utc)
        s = health.summarize_log(health.read_log_lines(), now - timedelta(hours=24))
        t = health.trade_summary(health.DB)
        return {
            "status": health.container_status(), "other_errors": len(s.other_errors),
            "network_errors": sum(s.network_by_hour.values()), "open": t["open"], "closed": t["closed"],
            "profit": t["profit"], "drawdown": t["drawdown"], "worst": t.get("worst", t["drawdown"]), "phase0": health.phase0_verdict(s, now),
            "network_peak": (lambda hr, n: f"{hr}:00 UTC'de {n}")(*s.network_by_hour.most_common(1)[0])
            if s.network_by_hour else None,
            "longest_gap": f"{health.hours(s.longest_gap)} ({s.longest_gap_start:%d.%m %H:%M} UTC'den itibaren;"
            " Mac uykusu ya da internet kesintisi)" if s.longest_gap_start else "yok",
        }  # fmt: skip
    except Exception as e:  # the report must still be written if docker is unreachable
        return {"status": f"okunamadı ({e.__class__.__name__})"}


def append_breadth(path: Path, line: str, header: str = BREADTH_HEADER) -> None:
    """Add today's breadth row; a second run on the same date replaces that date's row."""
    date = line.split(",", 1)[0]
    rows = path.read_text().splitlines()[1:] if path.exists() else []
    rows = [r for r in rows if not r.startswith(date + ",")] + [line]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join([header, *sorted(rows)]) + "\n")


FORWARD_NAMES = {"freqtrade": "VolTarget (ana bot)", "forward-adx20": "ADX20 (paralel bot)"}


def forward_rows() -> list[dict]:
    """Each dry-run bot's realized results from its own DB (read-only): judgement only, never tuning."""
    rows = []
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    for service, db in health.SERVICES.items():
        t = health.trade_summary(db)
        row = {"name": FORWARD_NAMES.get(service, service), "running": db.exists(), **t}
        try:  # container state + last-24h errors from that bot's own log
            row["status"] = health.container_status(service)
            row["errors"] = len(health.summarize_log(health.read_log_lines(service), since).other_errors)
        except Exception as e:  # the report must still be written if docker is unreachable
            row["status"] = f"okunamadı ({e.__class__.__name__})"
        rows.append(row)
    return rows


def prereg_lines() -> list[str]:
    """Fresh-only pre-registered ideas and their progress (never judged before their judge date)."""
    try:
        rows = prereg.load()
    except (OSError, ValueError) as e:
        return [f"ön kayıt dosyası okunamadı: {e}"]
    today = datetime.now(timezone.utc).date()
    bad = prereg.problems(rows)
    results = prereg.load_results()
    return [f"SORUN: {p}" for p in bad] + [f"{r['id']} {r['name']}: {prereg.progress(r, today, results)}" for r in rows]


def _prereg_rows() -> list[dict]:
    try:
        return prereg.load()
    except (OSError, ValueError):
        return []


def plan(with_nfi: bool, download: bool) -> list[tuple[str, list[str], bool]]:
    """(title, ft.py arguments, capture output for the report?) in run order."""
    steps: list[tuple[str, list[str], bool]] = []
    if download:
        steps.append(("download core", ["download"], False))
        for universe in [u for u in UNIVERSES if u != "core"] + list(WATCH_UNIVERSES):
            steps.append((f"download {universe}", ["download", "--universe", universe], False))
        if with_nfi:
            steps.append(("download 5m", ["download", "--fine"], False))
    for universe in UNIVERSES:
        extra = [] if universe == "core" else ["--universe", universe]
        steps.append((f"backtest {universe}", ["backtest", "--slice", "fresh", *extra, "--strategy", *CANDIDATES, *WATCH], False))
    for universe, names in WATCH_UNIVERSES.items():
        steps.append((f"backtest {universe} (watch)", ["backtest", "--slice", "fresh", "--universe", universe, "--strategy", *names], False))
    if with_nfi:
        steps.append(("backtest NFI", ["backtest", "--slice", "fresh", "--strategy", "NostalgiaForInfinityX8"], False))
    shown = CANDIDATES + (["NostalgiaForInfinityX8"] if with_nfi else [])
    for universe in UNIVERSES:
        extra = [] if universe == "core" else ["--universe", universe]
        names = shown if universe == "core" else CANDIDATES
        steps.append((f"bots {universe}", ["bots", "--slice", "fresh", *extra, "--strategy", *names, *WATCH], True))
    for universe, names in WATCH_UNIVERSES.items():
        steps.append((f"bots {universe} (watch)", ["bots", "--slice", "fresh", "--universe", universe, "--strategy", *names], True))
    steps.append(("expected", ["expected"], True))  # fresh result vs its expected range (judging only)
    steps.append(("forward-risk", ["forward-risk"], True))  # next 12 months from history, kill switch latched
    steps.append(("execution", ["execution"], True))
    steps.append(("ai-score", ["ai-score"], True))  # score AI views whose 7 days have passed
    steps.append(("explain", ["explain"], True))  # every trade in plain Turkish -> trades-explained.md  # order quality (read-only)
    for coin in CHART_COINS:  # plain-Turkish chart reading of the bot's coins -> report section 8
        steps.append((f"chart {coin}", ["chart", "--pair", coin, "--tr"], True))
    steps.append(("scan pool", ["scan", "--csv"], True))  # record only: market breadth per day
    if any(prereg.is_due(r, datetime.now(timezone.utc).date()) for r in _prereg_rows()):
        steps.append(("prereg judge", ["prereg-judge", "--due"], True))  # fresh-only rows whose judge date came
    return steps


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="daily forward check on the fresh slice")
    parser.add_argument("--no-download", action="store_true")
    parser.add_argument("--with-nfi", action="store_true", help="also run NFI X8 (5m, slow)")
    args = parser.parse_args(argv)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report = [f"# Taze veri kontrolü {today}", "",
              "Sadece yargı için. Kurallar bu sonuçlara bakılarak değiştirilmez (docs/journal.md).", ""]  # fmt: skip
    captured: dict[str, str] = {}
    for title, ft_args, capture in plan(args.with_nfi, not args.no_download):
        print(f"== {title}: ft.py {' '.join(ft_args)}", flush=True)
        code, out = run(ft_args, capture)
        if code != 0:
            print(f"FAILED ({code}): {title}")
            return code
        if capture:
            captured[title] = out
            print(out)
            for ln in out.splitlines():
                if ln.startswith("breadth_csv: "):
                    append_breadth(BREADTH_CSV, ln.removeprefix("breadth_csv: ").strip())
            report += [f"## {title}", "", "```", table_lines(out), "```", ""]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{today}.md"
    path.write_text("\n".join(report))
    print(f"report: {path.relative_to(ROOT)}")
    explained = kaan_report.clean(captured.get("explain", ""))
    if explained:
        (OUT_DIR / "trades-explained.md").write_text(explained + "\n")
    short = kaan_report.write(OUT_DIR, today, kaan_report.render(
        today, health_summary(), captured.get("scan pool", ""), kaan_report.breadth_rows(BREADTH_CSV),
        captured.get("bots core", ""), captured.get("bots core_gold (watch)", ""), captured.get("execution", ""),
        kaan_report.ai_counts(OUT_DIR / "ai-views.md"), captured.get("expected", ""), explained,
        captured.get("ai-score", ""), [captured.get(f"chart {c}", "") for c in CHART_COINS],
        captured.get("forward-risk", ""), prereg_lines(), forward_rows(),
    ))  # fmt: skip
    print(f"short report: {short.relative_to(ROOT)} (+ latest.md)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
