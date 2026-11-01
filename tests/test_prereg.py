"""Tests for scripts/prereg.py: fresh-only pre-registration with a locked criterion."""

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import prereg  # noqa: E402


def row(**kw):
    r = {"id": "F1", "name": "X", "kind": "strategy", "idea": "i", "criterion": "c", "start": "2026-11-02",
         "judge": "2027-02-01", "min_trades": "50", "lock": "", "status": "active"}  # fmt: skip
    r.update(kw)
    r.setdefault("lock", "")
    if not kw.get("lock"):
        r["lock"] = prereg.lock_hash(r)
    return r


def test_real_register_is_valid():
    rows = prereg.load()
    assert prereg.problems(rows) == []
    assert {r["name"] for r in rows} >= {"TrendEmaVolTargetDaily", "Weekly DCA 50% + VolTarget 50%"}


def test_editing_the_criterion_breaks_the_lock():
    r = row()
    r["criterion"] = "c but easier"
    assert any("lock mismatch" in p for p in prereg.problems([r]))


def test_relock_refused_on_or_after_start():
    rows = [row()]
    rows[0]["criterion"] = "changed"
    prereg.relock(rows, "F1", date(2026, 11, 1))  # before start: allowed
    assert prereg.problems(rows) == []
    rows[0]["criterion"] = "changed again"
    with pytest.raises(SystemExit, match="no longer change"):
        prereg.relock(rows, "F1", date(2026, 11, 2))


def test_progress_text():
    r = row()
    assert prereg.progress(r, date(2026, 11, 1)).startswith("başlamadı")
    assert prereg.progress(r, date(2026, 12, 2)) == "henüz hüküm yok (30/91 gün)"
    assert "hüküm günü geldi" in prereg.progress(r, date(2027, 2, 1))


def test_bad_rows_reported():
    p = prereg.problems([row(), row(judge="2026-11-01"), row(id="F2", min_trades="x", status="maybe")])
    assert any("duplicate id F1" in x for x in p) and any("after the start" in x for x in p)
    assert any("whole number" in x for x in p) and any("status" in x for x in p)


def test_daily_report_lists_the_preregistered_ideas():
    import daily
    import kaan_report

    lines = daily.prereg_lines()
    assert any("TrendEmaVolTargetDaily" in ln for ln in lines) and not any(ln.startswith("SORUN") for ln in lines)
    text = kaan_report.render("2026-11-02", {}, "", [], "", "", "", (0, 0), prereg=["F001 X: henüz hüküm yok (1/365 gün)"])
    assert "Ön kayıtlı fikirler" in text and "henüz hüküm yok (1/365 gün)" in text
