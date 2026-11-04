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


CAND = {"calmar": 1.5, "max_drawdown": 0.08, "trades": 70}
BASE = {"calmar": 1.0, "max_drawdown": 0.10, "trades": 80}
WORSE = {"calmar": 0.5, "max_drawdown": 0.08, "trades": 70}


def res(verdict="PASS", boot_p=""):
    return {"id": "F1", "judged_on": "2027-02-01", "verdict": verdict, "candidate_calmar": "1.5", "baseline_calmar": "1.0", "trades": "70", "boot_p": boot_p}


def test_add_months_clips_to_the_end_of_the_month():
    assert prereg.add_months(date(2027, 5, 2), 6) == date(2027, 11, 2)
    assert prereg.add_months(date(2027, 8, 31), 6) == date(2028, 2, 29)
    assert prereg.add_months(date(2027, 11, 1), 3) == date(2028, 2, 1)


def test_stage_path_of_a_row():
    assert prereg.stage("F1", {}, {}) is None
    assert prereg.stage("F1", {"F1": res("FAIL")}, {}) == "FAIL"
    assert prereg.stage("F1", {"F1": res("yetersiz")}, {}) == "yetersiz"
    assert prereg.stage("F1", {"F1": res()}, {}) == "ADAY"
    assert prereg.stage("F1", {"F1": res()}, {"F1": res()}) == "DOĞRULANDI"
    assert prereg.stage("F1", {"F1": res()}, {"F1": res("FAIL")}) == "ELENDİ"
    assert prereg.stage("F1", {"F1": res()}, {"F1": res("yetersiz")}) == "ADAY-yetersiz"


def test_a_pass_becomes_aday_and_is_judged_again_alone_on_the_next_6_months(tmp_path):
    rows, first, second = [row()], tmp_path / "r.csv", tmp_path / "c.csv"
    prereg.record(rows, "F1", CAND, BASE, date(2027, 2, 1), first, boot_p=0.04)
    results = prereg.load_results(first)
    assert results["F1"]["boot_p"] == "0.0400"
    assert prereg.confirm_timerange(rows[0]) == "20270201-20270801"
    assert "ADAY: tek başına 2. yargı 2027-08-01" in prereg.progress(rows[0], date(2027, 3, 1), results)
    with pytest.raises(SystemExit, match="second judgement"):
        prereg.record_confirm(rows, "F1", CAND, BASE, date(2027, 7, 31), first, second)  # no peeking here either
    assert prereg.record_confirm(rows, "F1", CAND, BASE, date(2027, 8, 1), first, second) == "DOĞRULANDI"
    assert "→ DOĞRULANDI" in prereg.progress(rows[0], date(2027, 9, 1), results, prereg.load_results(second))
    with pytest.raises(SystemExit):
        prereg.record_confirm(rows, "F1", CAND, BASE, date(2027, 8, 2), first, second)  # once only


def test_second_failure_eliminates_and_uses_the_same_locked_rule(tmp_path):
    rows, first, second = [row()], tmp_path / "r.csv", tmp_path / "c.csv"
    prereg.record(rows, "F1", CAND, BASE, date(2027, 2, 1), first)
    assert prereg.record_confirm(rows, "F1", WORSE, BASE, date(2027, 8, 1), first, second) == "ELENDİ"


def test_the_second_stage_changes_no_locked_field():
    before = row()
    lock = before["lock"]
    assert prereg.lock_hash(before) == lock and prereg.problems([before]) == []
    assert not {"boot_p", "status"} & set(prereg.LOCKED)


def test_a_failed_row_is_never_judged_again():
    assert not prereg.confirm_due(row(), {"F1": res("FAIL")}, {}, date(2030, 1, 1))
    assert not prereg.confirm_due(row(), {}, {}, date(2030, 1, 1))
    assert prereg.confirm_due(row(), {"F1": res()}, {}, date(2027, 8, 1))


def test_holm_known_values():
    got = prereg.holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert abs(got["a"] - 0.03) < 1e-12 and abs(got["c"] - 0.06) < 1e-12 and abs(got["b"] - 0.06) < 1e-12  # never decreases
    assert prereg.holm({"a": 0.6, "b": 0.9}) == {"a": 1.0, "b": 1.0}
    assert prereg.holm({}) == {}


def test_family_warning_counts_rows_and_prints_holm_as_information():
    assert prereg.family_lines({"F1": res()}) == []
    lines = prereg.family_lines({"F1": res(boot_p="0.0100"), "F2": res(boot_p="0.0400"), "F3": res()})
    assert lines[0] == "Aynı anda 3 satır yargılandı. Şansla en az birinin geçmesi beklenir."
    assert "F1: block-bootstrap p 0.010, Holm 0.020" in lines[1] and "sadece bilgi" in lines[1] and len(lines) == 3


def test_bootstrap_p_finds_a_steady_lead_and_none_when_identical():
    import numpy as np

    import prereg_eval

    rng = np.random.default_rng(1)
    market = rng.normal(0.0, 0.01, 180)
    assert prereg_eval.bootstrap_p(market, market, runs=200) == 1.0  # same curve: never better
    assert prereg_eval.bootstrap_p(market + 0.01, market, runs=200) < 0.05
    assert prereg_eval.bootstrap_p(market - 0.01, market, runs=200) > 0.95
    assert prereg_eval.bootstrap_p(market[:5], market[:5]) is None  # too little data
    assert prereg_eval.bootstrap_p(market, market, runs=50) == prereg_eval.bootstrap_p(market, market, runs=50)  # seeded


def test_prereg_judge_runs_an_aday_row_alone_on_the_second_window_with_confirm(monkeypatch):
    import ft

    done = row(id="F8", start="2020-01-01", judge="2020-07-01", status="judged")
    monkeypatch.setattr(prereg, "load", lambda path=prereg.FILE: [done])
    monkeypatch.setattr(prereg, "load_results", lambda path=prereg.RESULTS: {"F8": {**res(), "id": "F8"}} if path == prereg.RESULTS else {})
    bt, ev = ft.build_commands(ft.parse_args(["prereg-judge", "--due"]))
    assert bt[bt.index("--timerange") + 1] == "20200701-20210101"
    assert ev[-1] == "--confirm" and ev[ev.index("--id") + 1] == "F8"
