"""Tests for the trial freeze (scripts/freeze.py, trials.py --open, prereg.py --open, ft.py trial)."""

import csv
import shutil
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import freeze  # noqa: E402
import ft  # noqa: E402
import prereg  # noqa: E402
import trials  # noqa: E402

T_ARGS = ["--name", "X", "--family", "f", "--idea", "i", "--criterion", "c"]
F_ARGS = ["--name", "X", "--kind", "strategy", "--idea", "i", "--criterion", "c", "--start", "2026-12-01", "--judge", "2027-06-01", "--min-trades", "50"]
TODAY = date(2026, 11, 5)


@pytest.fixture
def copies(tmp_path):
    t, f = tmp_path / "trials.csv", tmp_path / "pre.csv"
    shutil.copy(trials.TRIALS, t)
    shutil.copy(prereg.FILE, f)
    return t, f, tmp_path / "approvals.csv"


def test_only_ids_after_the_frozen_ones_are_new():
    assert not freeze.is_new("T162") and freeze.is_new("T163")
    assert not freeze.is_new("F013") and freeze.is_new("F014")
    assert not freeze.is_new("7")  # malformed: the register's own check reports it


def test_the_register_is_frozen_at_160_apart_from_approved_rows():
    approved_t = [i for i in freeze.load_approvals() if i.startswith("T")]
    assert trials.n_trials(trials.load()) - len(approved_t) == freeze.FROZEN_N


@pytest.mark.parametrize("flag", [[], ["--kaan-approved", ""], ["--kaan-approved", "   "]])
def test_opening_is_refused_without_a_real_approval_and_shows_the_rule(copies, capsys, flag):
    t, f, a = copies
    before = t.read_text(), f.read_text()
    with pytest.raises(SystemExit, match="kaan-approved"):
        trials.open_row(T_ARGS + flag, t, a)
    with pytest.raises(SystemExit, match="kaan-approved"):
        prereg.open_row(F_ARGS + flag, TODAY, f, a)
    assert freeze.WARNING in capsys.readouterr().out
    assert (t.read_text(), f.read_text()) == before and not a.exists()


def test_approved_trial_gets_the_next_id_counts_in_n_and_records_who_approved(copies):
    t, _, a = copies
    n = trials.n_trials(trials.load(t))
    assert trials.open_row([*T_ARGS, "--kaan-approved", "msg-42"], t, a) == "T163"
    rows = trials.load(t)
    assert rows[-1]["verdict"] == "PENDING" and trials.n_trials(rows) == n + 1
    assert freeze.load_approvals(a) == {"T163": "msg-42"}
    assert freeze.unapproved(["T163"], freeze.load_approvals(a)) == []


def test_approved_fresh_row_is_locked_from_birth(copies):
    _, f, a = copies
    assert prereg.open_row([*F_ARGS, "--kaan-approved", "2026-11-05"], TODAY, f, a) == "F014"
    row = prereg.load(f)[-1]
    assert row["lock"] == prereg.lock_hash(row) and row["status"] == "active"


def test_fresh_row_must_start_in_the_future(copies):
    _, f, a = copies
    args = [*F_ARGS, "--kaan-approved", "x"]
    args[args.index("2026-12-01")] = "2026-11-05"
    with pytest.raises(SystemExit, match="after today"):
        prereg.open_row(args, TODAY, f, a)


def test_a_row_added_by_hand_is_caught_by_the_checks():
    t = dict.fromkeys(trials.FIELDS, "") | {"id": "T163", "name": "Sneaky", "verdict": "PENDING"}
    assert any("no approval line" in p for p in trials.problems([t], set()))
    r = {"id": "F014", "name": "X", "kind": "strategy", "idea": "i", "criterion": "c", "start": "2026-12-01",
         "judge": "2027-06-01", "min_trades": "50", "lock": "", "status": "active"}  # fmt: skip
    r["lock"] = prereg.lock_hash(r)
    assert any("no approval line" in p for p in prereg.problems([r]))
    with pytest.raises(SystemExit, match="F014"):
        prereg.relock([r], "F014", TODAY)


def test_ft_trial_refuses_a_strategy_with_no_row_but_runs_a_registered_one():
    with pytest.raises(SystemExit, match="no row in docs/trials.csv"):
        ft.build_commands(ft.parse_args(["trial", "--strategy", "BrandNewIdea"]))
    with pytest.raises(SystemExit, match="no row in docs/trials.csv"):
        ft.build_commands(ft.parse_args(["trial", "--strategy", "TrendEmaVolTargetBtcDom", "--neighbours", "BrandNewIdea"]))
    assert ft.build_commands(ft.parse_args(["trial", "--strategy", "TrendEmaVolTargetBtcDom"]))


def test_approval_file_starts_empty_with_its_header():
    with freeze.APPROVALS.open(newline="") as f:
        assert csv.DictReader(f).fieldnames == freeze.FIELDS
