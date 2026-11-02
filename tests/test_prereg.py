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
    assert prereg.progress(r, date(2026, 12, 2)) == "henüz hüküm yok (30/91 gün, 61 gün kaldı)"
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


def test_judge_row_criterion():
    base = {"calmar": 1.0, "max_drawdown": 0.10, "trades": 80}
    assert prereg.judge_row({"calmar": 1.2, "max_drawdown": 0.10, "trades": 60}, base, 50) == "PASS"
    assert prereg.judge_row({"calmar": 1.2, "max_drawdown": 0.11, "trades": 60}, base, 50) == "FAIL"  # deeper fall
    assert prereg.judge_row({"calmar": 0.9, "max_drawdown": 0.05, "trades": 60}, base, 50) == "FAIL"
    assert prereg.judge_row({"calmar": 9.9, "max_drawdown": 0.01, "trades": 49}, base, 50) == "yetersiz"


def test_record_refuses_before_judge_date_and_writes_once(tmp_path):
    rows = [row()]
    cand = {"calmar": 1.5, "max_drawdown": 0.08, "trades": 70}
    base = {"calmar": 1.0, "max_drawdown": 0.10, "trades": 80}
    out = tmp_path / "res.csv"
    with pytest.raises(SystemExit):
        prereg.record(rows, "F1", cand, base, date(2027, 1, 31), out)  # one day early: no peeking
    assert prereg.record(rows, "F1", cand, base, date(2027, 2, 1), out) == "PASS"
    assert rows[0]["status"] == "judged" and prereg.problems(rows) == []  # status is not a locked field
    with pytest.raises(SystemExit):
        prereg.record(rows, "F1", cand, base, date(2027, 2, 2), out)  # judged once only
    res = prereg.load_results(out)
    assert res["F1"]["verdict"] == "PASS" and "HÜKÜM 2027-02-01: PASS" in prereg.progress(rows[0], date(2027, 3, 1), res)


def test_timerange_is_the_rows_own_window():
    assert prereg.timerange(row()) == "20261102-20270201"


def test_prereg_judge_command_refuses_early_and_plans_backtest_then_eval(monkeypatch):
    import ft

    early = row(id="F9", judge="2099-01-01")
    due = row(id="F8", start="2020-01-01", judge="2020-07-01")
    mix = row(id="F7", kind="mix", start="2020-01-01", judge="2020-07-01")
    monkeypatch.setattr(prereg, "load", lambda path=prereg.FILE: [early, due, mix])
    with pytest.raises(SystemExit):
        ft.build_commands(ft.parse_args(["prereg-judge", "--id", "F9"]))
    steps = ft.build_commands(ft.parse_args(["prereg-judge", "--due"]))
    assert len(steps) == 2  # F8: backtest + eval; F7 (mix) is left for a human; F9 not due
    bt, ev = steps
    assert bt[bt.index("--timerange") + 1] == "20200101-20200701" and "TrendEmaVolTarget" in bt
    assert "--no-kill-switch" not in bt and "/freqtrade/scripts/prereg_eval.py" in ev and ev[-1] == "F8"


def test_daily_adds_the_judge_step_only_when_a_row_is_due(monkeypatch):
    import daily

    monkeypatch.setattr(daily, "_prereg_rows", lambda: [row()])  # judge 2027-02-01: not due today
    assert not any(t == "prereg judge" for t, _, _ in daily.plan(False, False))
    monkeypatch.setattr(daily, "_prereg_rows", lambda: [row(start="2020-01-01", judge="2020-07-01")])
    assert any(t == "prereg judge" for t, _, _ in daily.plan(False, False))
