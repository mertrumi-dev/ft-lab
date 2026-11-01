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
