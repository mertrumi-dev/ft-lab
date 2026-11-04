"""Fresh-only pre-registration: ideas written down now, judged only on data that does not exist yet.

    python3 scripts/prereg.py              # check docs/fresh/preregistered.csv, print each row's progress
    python3 scripts/prereg.py --lock ID    # (re)write ID's lock hash; refused on/after its start date
    python3 scripts/prereg.py --open --kaan-approved "<message id or date>" --name X --kind strategy --idea I
                              --criterion C --start YYYY-MM-DD --judge YYYY-MM-DD --min-trades 50
                                           # new row. Frozen: refused without the approval (scripts/freeze.py)

Every row has a start date (data before it is never counted) and a fixed judge date. Its
criterion is locked by a hash of (name, idea, criterion, start, judge, min_trades): after the
start date any change to those fields is reported as a PROBLEM and the run fails, and --lock
is refused, so nobody (human or AI) can move the goalposts after seeing data.
Until the judge date a row only shows "henüz hüküm yok (X/N gün)". Stdlib only (runs on the Mac).

Multiple-comparison layer (on top; criteria and hashes untouched). Many rows judged together means
some pass by luck, so a first PASS is only "ADAY". An ADAY row is judged again ALONE, on the same
locked criterion, on the next 6 months after its judge date: PASS again = "DOĞRULANDI", else "ELENDİ".
A block-bootstrap p-value per row (prereg_eval.py) and its Holm-adjusted value are information only:
they never change a verdict.
"""

import argparse
import calendar
import csv
import hashlib
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import freeze  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "docs" / "fresh" / "preregistered.csv"
FIELDS = ["id", "name", "kind", "idea", "criterion", "start", "judge", "min_trades", "lock", "status"]
LOCKED = ("name", "idea", "criterion", "start", "judge", "min_trades")
STATUSES = ("active", "judged", "yetersiz")
RESULTS = ROOT / "docs" / "fresh" / "prereg-results.csv"  # append-only: one line per judged row
RESULT_FIELDS = ["id", "judged_on", "verdict", "candidate_calmar", "baseline_calmar", "candidate_dd", "baseline_dd", "trades", "boot_p"]
CONFIRMS = ROOT / "docs" / "fresh" / "prereg-confirm.csv"  # append-only: the second, alone judgement of ADAY rows
CONFIRM_MONTHS = 6


def lock_hash(row: dict) -> str:
    return hashlib.sha256("|".join(row[k].strip() for k in LOCKED).encode()).hexdigest()[:16]


def load(path: Path = FILE) -> list[dict]:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != FIELDS:
            raise ValueError(f"columns must be {FIELDS}, got {reader.fieldnames}")
        return list(reader)


def problems(rows: list[dict]) -> list[str]:
    out, seen = [], set()
    for r in rows:
        rid = r["id"]
        if rid in seen:
            out.append(f"duplicate id {rid}")
        seen.add(rid)
        try:
            start, judge = date.fromisoformat(r["start"]), date.fromisoformat(r["judge"])
        except ValueError:
            out.append(f"{rid}: start/judge must be YYYY-MM-DD")
            continue
        if judge <= start:
            out.append(f"{rid}: judge date must be after the start date")
        if not r["min_trades"].isdigit():
            out.append(f"{rid}: min_trades must be a whole number")
        if r["status"] not in STATUSES:
            out.append(f"{rid}: status {r['status']!r} not in {STATUSES}")
        if r["lock"] != lock_hash(r):
            out.append(f"{rid}: criterion/idea/dates changed after registration (lock mismatch): not allowed")
    out += [f"{i}: opened after the freeze with no approval line: {freeze.WARNING}" for i in freeze.unapproved([r["id"] for r in rows])]
    return out


def add_months(d: date, months: int) -> date:
    """Same day of the month, `months` later; clipped to the month's last day (Aug 31 -> Feb 28)."""
    total = d.month - 1 + months
    year, month = d.year + total // 12, total % 12 + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def confirm_end(row: dict) -> date:
    """The second window is [judge, this date): prices nobody had at the first judgement."""
    return add_months(date.fromisoformat(row["judge"]), CONFIRM_MONTHS)


def confirm_timerange(row: dict) -> str:
    return f"{row['judge'].replace('-', '')}-{confirm_end(row).strftime('%Y%m%d')}"


def stage(rid: str, results: dict, confirms: dict) -> str | None:
    """Where a row stands: None (not judged), FAIL/yetersiz, ADAY, DOĞRULANDI, ELENDİ or ADAY-yetersiz."""
    first = results.get(rid)
    if not first:
        return None
    if first["verdict"] != "PASS":
        return first["verdict"]
    second = confirms.get(rid)
    if not second:
        return "ADAY"
    return {"PASS": "DOĞRULANDI", "FAIL": "ELENDİ"}.get(second["verdict"], "ADAY-yetersiz")


def confirm_due(row: dict, results: dict, confirms: dict, today: date) -> bool:
    return stage(row["id"], results, confirms) == "ADAY" and today >= confirm_end(row)


def holm(pvalues: dict[str, float]) -> dict[str, float]:
    """Holm-adjusted p-values: the smallest p x n, the next x (n-1), ..., never decreasing, at most 1."""
    n, running, out = len(pvalues), 0.0, {}
    for i, (rid, p) in enumerate(sorted(pvalues.items(), key=lambda kv: kv[1])):
        running = max(running, min(1.0, p * (n - i)))
        out[rid] = running
    return out


def family_lines(results: dict) -> list[str]:
    """The warning for rows judged together + each row's p-values. Information only."""
    if len(results) < 2:
        return []
    lines = [f"Aynı anda {len(results)} satır yargılandı. Şansla en az birinin geçmesi beklenir."]
    ps = {rid: float(r["boot_p"]) for rid, r in results.items() if r.get("boot_p")}
    adjusted = holm(ps)
    lines += [f"{rid}: block-bootstrap p {ps[rid]:.3f}, Holm {adjusted[rid]:.3f} (sadece bilgi, hükmü değiştirmez)" for rid in sorted(ps)]
    return lines


def progress(row: dict, today: date, results: dict | None = None, confirms: dict | None = None) -> str:
    results, confirms = results or {}, confirms or {}
    res = results.get(row["id"])
    if res:
        text = (f"HÜKÜM {res['judged_on']}: {res['verdict']} (Calmar {float(res['candidate_calmar']):.2f} vs "
                f"VolTarget {float(res['baseline_calmar']):.2f}, {res['trades']} işlem)")  # fmt: skip
        now = stage(row["id"], results, confirms)
        if now == "ADAY":
            when = confirm_end(row)
            text += f" → ADAY: tek başına 2. yargı {when}" if today < when else " → ADAY: 2. yargı günü geldi: `python3 scripts/ft.py prereg-judge --due`"
        elif now in ("DOĞRULANDI", "ELENDİ", "ADAY-yetersiz"):
            c = confirms[row["id"]]
            text += f" → {now} (2. yargı {c['judged_on']}: Calmar {float(c['candidate_calmar']):.2f} vs {float(c['baseline_calmar']):.2f})"
        return text
    start, judge = date.fromisoformat(row["start"]), date.fromisoformat(row["judge"])
    total = (judge - start).days
    if today < start:
        return f"başlamadı (başlangıç {start}, hüküm {judge})"
    done = min((today - start).days, total)
    if today < judge:
        return f"henüz hüküm yok ({done}/{total} gün, {total - done} gün kaldı)"
    return f"hüküm günü geldi ({total}/{total} gün): `python3 scripts/ft.py prereg-judge --due`"


def is_due(row: dict, today: date) -> bool:
    """Judge only on/after the judge date and only once (status still active)."""
    return row["status"] == "active" and today >= date.fromisoformat(row["judge"])


def timerange(row: dict) -> str:
    """Freqtrade --timerange for the row's own window [start, judge)."""
    return f"{row['start'].replace('-', '')}-{row['judge'].replace('-', '')}"


def judge_row(cand: dict, base: dict, min_trades: int) -> str:
    """The criterion every row shares: Calmar higher AND max drawdown not higher; too few trades = yetersiz."""
    if cand["trades"] < min_trades:
        return "yetersiz"
    return "PASS" if cand["calmar"] > base["calmar"] and cand["max_drawdown"] <= base["max_drawdown"] else "FAIL"


def load_results(path: Path = RESULTS) -> dict[str, dict]:
    if not path.exists():
        return {}
    with path.open(newline="") as f:
        return {r["id"]: r for r in csv.DictReader(f)}


def _append(path: Path, rid: str, verdict: str, cand: dict, base: dict, today: date, boot_p: float | None) -> None:
    new = not path.exists()
    with path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        if new:
            w.writeheader()
        w.writerow({"id": rid, "judged_on": today.isoformat(), "verdict": verdict,
                    "candidate_calmar": f"{cand['calmar']:.4f}", "baseline_calmar": f"{base['calmar']:.4f}",
                    "candidate_dd": f"{cand['max_drawdown']:.4f}", "baseline_dd": f"{base['max_drawdown']:.4f}",
                    "trades": cand["trades"], "boot_p": "" if boot_p is None else f"{boot_p:.4f}"})  # fmt: skip


def record(rows: list[dict], rid: str, cand: dict, base: dict, today: date, path: Path = RESULTS, boot_p: float | None = None) -> str:
    """Apply the criterion, append the result line, set the row's status. Returns the verdict."""
    row = next(r for r in rows if r["id"] == rid)
    if not is_due(row, today):
        raise SystemExit(f"Refusing: {rid} is not due (judge {row['judge']}, status {row['status']}).")
    verdict = judge_row(cand, base, int(row["min_trades"]))
    _append(path, rid, verdict, cand, base, today, boot_p)
    row["status"] = "yetersiz" if verdict == "yetersiz" else "judged"
    return verdict


def record_confirm(rows: list[dict], rid: str, cand: dict, base: dict, today: date, results_path: Path = RESULTS,
                   path: Path = CONFIRMS, boot_p: float | None = None) -> str:  # fmt: skip
    """Second, alone judgement of an ADAY row on the same locked criterion. Returns the new stage."""
    row = next(r for r in rows if r["id"] == rid)
    results, confirms = load_results(results_path), load_results(path)
    if not confirm_due(row, results, confirms, today):
        raise SystemExit(f"Refusing: {rid} is not due for its second judgement (stage {stage(rid, results, confirms)}, window ends {confirm_end(row)}).")
    _append(path, rid, judge_row(cand, base, int(row["min_trades"])), cand, base, today, boot_p)
    return stage(rid, results, load_results(path))


def relock(rows: list[dict], rid: str, today: date) -> None:
    if freeze.unapproved([rid]):  # locking a hand-added row would be opening it
        raise SystemExit(f"Refusing: {rid}. {freeze.WARNING}")
    row = next(r for r in rows if r["id"] == rid)
    if today >= date.fromisoformat(row["start"]):
        raise SystemExit(f"Refusing: {rid} started on {row['start']}; its criterion can no longer change.")
    row["lock"] = lock_hash(row)


def save(rows: list[dict], path: Path = FILE) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def next_id(rows: list[dict]) -> str:
    return f"F{max(int(r['id'][1:]) for r in rows) + 1:03d}"


def open_row(argv: list[str], today: date, path: Path = FILE, approvals_path: Path = freeze.APPROVALS) -> str:
    """Pre-register one new fresh-only row, locked from birth. Returns its id."""
    p = argparse.ArgumentParser(prog="prereg.py --open")
    p.add_argument("--kaan-approved")
    for field in ("name", "kind", "idea", "criterion", "start", "judge", "min-trades"):
        p.add_argument(f"--{field}")
    a = p.parse_args(argv)
    approved = freeze.require_approval(a.kaan_approved)  # the refusal comes before anything else is asked
    if not all((a.name, a.kind, a.idea, a.criterion, a.start, a.judge, a.min_trades)):
        raise SystemExit("Refusing: every field is needed (--name --kind --idea --criterion --start --judge --min-trades).")
    if date.fromisoformat(a.start) <= today:
        raise SystemExit(f"Refusing: start {a.start} must be after today: a fresh row counts only data that does not exist yet.")
    rows = load(path)
    row = {"id": next_id(rows), "name": a.name, "kind": a.kind, "idea": a.idea, "criterion": a.criterion, "start": a.start,
           "judge": a.judge, "min_trades": a.min_trades, "lock": "", "status": "active"}  # fmt: skip
    row["lock"] = lock_hash(row)
    freeze.record(row["id"], approved, today, approvals_path)
    save([*rows, row], path)
    return row["id"]


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    today = datetime.now(timezone.utc).date()
    if argv[:1] == ["--open"]:
        print(f"{open_row(argv[1:], today)}: opened, locked")
        return 0
    rows = load()
    if argv[:1] == ["--lock"]:
        relock(rows, argv[1], today)
        save(rows)
        print(f"{argv[1]}: locked")
        return 0
    found = problems(rows)
    for p in found:
        print("PROBLEM:", p)
    results, confirms = load_results(), load_results(CONFIRMS)
    for r in rows:
        print(f"prereg {r['id']} {r['name']}: {progress(r, today, results, confirms)}")
    for line in family_lines(results):
        print(line)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
