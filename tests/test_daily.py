"""Tests for scripts/daily.py (daily forward check)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import daily  # noqa: E402


def test_plan_only_touches_fresh_slice():
    for _, args, _ in daily.plan(with_nfi=True, download=True):
        if "--slice" in args:
            assert args[args.index("--slice") + 1] == "fresh"
        assert "--final-test" not in args


def test_plan_order_download_backtest_then_report():
    titles = [t for t, _, _ in daily.plan(with_nfi=False, download=True)]
    assert titles[0].startswith("download")
    assert titles.index("backtest core") < titles.index("bots core")
    assert all(not t.startswith("download") for t in [t for t, _, _ in daily.plan(False, download=False)])


def test_nfi_is_opt_in():
    flat = [a for _, args, _ in daily.plan(False, True) for a in args]
    assert "NostalgiaForInfinityX8" not in flat and "--fine" not in flat
    flat = [a for _, args, _ in daily.plan(True, True) for a in args]
    assert "NostalgiaForInfinityX8" in flat and "--fine" in flat


def test_candidates_include_the_live_bot_strategy():
    assert daily.CANDIDATES[0] == "TrendEma"


def test_watch_rows_are_tracked_on_fresh_only():
    steps = daily.plan(with_nfi=False, download=True)
    flat = [a for _, args, _ in steps for a in args]
    assert "TrendEmaVolTarget2h" in flat
    gold = [args for t, args, _ in steps if "core_gold" in args]
    assert any(a[0] == "backtest" for a in gold) and any(a[0] == "bots" for a in gold)
    assert all(a[a.index("--slice") + 1] == "fresh" for _, a, _ in steps if "--slice" in a)
    titles = [t for t, _, _ in steps]
    assert {"download alt2022", "download alt2023", "download alt2024", "download core_gold"} <= set(titles)


def test_speed_ensemble_legs_are_both_tracked():
    flat = [a for _, args, _ in daily.plan(False, True) for a in args]
    assert "TrendEmaVolTarget" in flat and "TrendEmaVolTarget2h" in flat


def test_append_breadth_is_idempotent_per_date(tmp_path):
    p = tmp_path / "b.csv"
    daily.append_breadth(p, "2026-11-01,61,0.130,8,0,below,below,below,below,below")
    daily.append_breadth(p, "2026-11-02,61,0.200,9,1,trend,below,below,below,below")
    daily.append_breadth(p, "2026-11-01,61,0.150,8,0,below,below,below,below,below")  # rerun same day
    lines = p.read_text().splitlines()
    assert lines[0] == daily.BREADTH_HEADER
    assert lines[1:] == ["2026-11-01,61,0.150,8,0,below,below,below,below,below",
                         "2026-11-02,61,0.200,9,1,trend,below,below,below,below"]


def test_daily_runs_scan_with_csv_last():
    t, args, capture = daily.plan(False, True)[-1]
    assert args == ["scan", "--csv"] and capture


def test_run_step_retries_once_after_a_failure(monkeypatch):
    import daily

    calls = []
    results = iter([(1, ""), (0, "ok")])
    monkeypatch.setattr(daily, "run", lambda args, capture=False: (calls.append(args), next(results))[1])
    monkeypatch.setattr(daily.time, "sleep", lambda s: calls.append(("slept", s)))
    assert daily.run_step(["download"], False, wait_s=60) == (0, "ok")
    assert calls == [["download"], ("slept", 60), ["download"]]


def test_a_failed_step_is_reported_and_the_day_goes_on(monkeypatch, tmp_path):
    import daily

    monkeypatch.setattr(daily, "ROOT", tmp_path)
    monkeypatch.setattr(daily, "OUT_DIR", tmp_path)
    monkeypatch.setattr(daily, "BREADTH_CSV", tmp_path / "breadth.csv")
    monkeypatch.setattr(daily, "plan", lambda nfi, dl: [("download core", ["download"], False), ("expected", ["expected"], True)])
    monkeypatch.setattr(daily, "run_step", lambda args, capture: (2, "") if args == ["download"] else (0, "expected text"))
    monkeypatch.setattr(daily, "health_summary", lambda: {"status": "test"})
    monkeypatch.setattr(daily, "forward_rows", lambda: [])
    monkeypatch.setattr(daily.kaan_report, "write", lambda out_dir, today, text: out_dir / "short.md")
    assert daily.main(["--no-download"]) == 1  # still a non-zero exit: the failure is not hidden
    report = next(tmp_path.glob("20*.md")).read_text()
    assert "## download core" in report and "BAŞARISIZ" in report and "expected text" in report
