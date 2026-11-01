"""Tests for scripts/forward_risk.py: the kill-switch latch in the simulator."""

import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import forward_risk  # noqa: E402
import kaan_report  # noqa: E402


def test_latch_freezes_the_path_on_the_day_the_fall_reaches_20_percent():
    # +10%, then -10% x2 (from 1.1: 0.99, 0.891 -> fall 19%), -2% (0.873 -> 20.6%: latch), then +50% ignored
    paths = np.array([[0.10, -0.10, -0.10, -0.02, 0.50, 0.50]])
    eq, latch = forward_risk.latch_paths(paths)
    assert latch[0] == 4  # eq index 4 = after the 4th day
    assert eq[0, 4] == pytest.approx(1.1 * 0.9 * 0.9 * 0.98)
    assert np.allclose(eq[0, 5:], eq[0, 4])  # flat afterwards: no new trades (R13)


def test_no_latch_without_a_20_percent_fall_and_buy_and_hold_never_latches():
    paths = np.array([[0.05, -0.10, 0.05, -0.05]])
    eq, latch = forward_risk.latch_paths(paths)
    assert latch[0] == -1 and eq[0, -1] == pytest.approx(1.05 * 0.9 * 1.05 * 0.95)
    eq2, latch2 = forward_risk.latch_paths(np.array([[-0.5, 0.5]]), kill=None)
    assert latch2[0] == -1 and eq2[0, -1] == pytest.approx(0.75)


def test_stats_counts_kill_by_horizon_and_losses():
    days = forward_risk.DAYS
    calm = np.full(days, 0.001)
    crash_late = np.r_[np.full(200, 0.0), np.full(days - 200, -0.01)]  # reaches -20% around day 222
    s = forward_risk.stats(np.vstack([calm, crash_late]))
    assert s["p_kill_3 ay"] == 0.0 and s["p_kill_6 ay"] == 0.0 and s["p_kill_12 ay"] == 0.5
    assert s["p_loss"] == 0.5 and s["worst5"] < 0
    eq, latch = forward_risk.latch_paths(crash_late[None, :])
    assert latch[0] > 200 and eq[0, -1] == pytest.approx(0.8, abs=0.01)  # frozen at the -20% day


def test_report_line_goes_to_kaan_report():
    text = "Forward risk ...\nforward_line: VolTarget önümüzdeki 12 ay: ortanca +10%\n"
    out = kaan_report.render("2026-11-02", {}, "", [], "", "", "", (0, 0), forward_text=text)
    assert "İleriye risk: VolTarget önümüzdeki 12 ay: ortanca +10%" in out


def test_longest_underwater_is_the_longest_unbroken_stretch():
    eq = np.array([[1.0, 1.1, 1.0, 1.05, 1.2, 1.1, 1.0, 0.9, 1.3]])  # under: 2 days, then 3 days
    assert forward_risk.longest_underwater(eq)[0] == 3
