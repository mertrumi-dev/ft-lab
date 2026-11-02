"""Tests for scripts/trials.py and the real docs/trials.csv (the trial register)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import ft  # noqa: E402
import trials  # noqa: E402


def row(**kw):
    base = dict.fromkeys(trials.FIELDS, "")
    base.update(id="T001", name="X", verdict="FAIL")
    base.update(kw)
    return base


def test_real_register_is_valid_and_covers_every_backtested_strategy():
    rows = trials.load()
    assert trials.problems(rows, trials.tested_names(trials.EXPERIMENTS.read_text())) == []
    names = {r["name"] for r in rows}
    assert {"TrendEma", "TrendEmaVolTarget", "TrendEmaVolTargetBullVol", "TSMOM"} <= names
    assert next(r for r in rows if r["name"] == "NostalgiaForInfinityX8")["verdict"] == "REFERENCE"


def test_problems_found():
    rows = [row(), row(name="Y", verdict="MAYBE", train_core_calmar="abc"), row(id="7", name="Z")]
    p = trials.problems(rows, {"X", "Missing"})
    assert any("duplicate id T001" in x for x in p)
    assert any("verdict 'MAYBE'" in x for x in p)
    assert any("is not a number" in x for x in p)
    assert any("id must look like" in x for x in p)
    assert any("missing from trials.csv: Missing" in x for x in p)


def test_blank_numbers_are_allowed_and_n_excludes_references():
    rows = [row(), row(id="T002", name="R", verdict="REFERENCE"), row(id="T003", name="N", verdict="NEIGHBOUR")]
    assert trials.problems(rows, set()) == []
    assert trials.n_trials(rows) == 2


def test_tested_names_reads_the_strategy_column():
    text = "| Zaman | Komut | Strateji | Dilim | Not |\n|---|---|---|---|---|\n| 2026-11-01 03:00 | backtest | A, B | train | |\n"
    assert trials.tested_names(text) == {"A", "B"}


def test_ft_deflated_passes_n_from_the_register():
    cmd = ft.build_commands(ft.parse_args(["deflated"]))[0]
    assert cmd[-1] == str(trials.n_trials(trials.load())) and cmd[-2].endswith("deflated.py")


def test_find_reports_earlier_trials_and_journal_lines():
    rows = [row(name="TrendEmaAdx", idea="ADX > 20 filter", notes=""), row(id="T002", name="Other", idea="x", notes="")]
    hits = trials.find(rows, "- Tur 3: ADX (1,28) FAIL\n- unrelated", ["adx"])
    assert hits[0].startswith("T001") and any(h.startswith("journal: - Tur 3: ADX") for h in hits) and len(hits) == 2
    assert trials.find(rows, "", ["nothing-like-this"]) == []


def test_find_uses_synonyms_so_renamed_ideas_are_caught():
    """T150 'relative strength' was a near-copy of T107 'kesitsel momentum / üst yarı'."""
    rows = [row(name="TrendEmaVolTargetMomHalf", idea="30 günlük getirisi grubun üst yarısında (kesitsel momentum)", notes="")]
    assert trials.find(rows, "", ["strength"])[0].startswith("T001")
    assert trials.find(rows, "", ["relative"]) and trials.find(rows, "", ["rank"])
    assert trials.find(rows, "", ["strength", "volume"]) == []  # still AND across words
    assert trials.alternatives("hacim") == trials.alternatives("volume") and trials.alternatives("xyz") == ("xyz",)


def test_real_register_finds_t107_by_strength():
    hits = trials.find(trials.load(), "", ["strength"])
    assert any(h.startswith("T107") for h in hits)
