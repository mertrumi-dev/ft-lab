"""Fresh-only pre-registration: ideas written down now, judged only on data that does not exist yet.

    python3 scripts/prereg.py              # check docs/fresh/preregistered.csv, print each row's progress
    python3 scripts/prereg.py --lock ID    # (re)write ID's lock hash; refused on/after its start date

Every row has a start date (data before it is never counted) and a fixed judge date. Its
criterion is locked by a hash of (name, idea, criterion, start, judge, min_trades): after the
start date any change to those fields is reported as a PROBLEM and the run fails, and --lock
is refused, so nobody (human or AI) can move the goalposts after seeing data.
Until the judge date a row only shows "henüz hüküm yok (X/N gün)". Stdlib only (runs on the Mac).
"""

import csv
import hashlib
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "docs" / "fresh" / "preregistered.csv"
FIELDS = ["id", "name", "kind", "idea", "criterion", "start", "judge", "min_trades", "lock", "status"]
LOCKED = ("name", "idea", "criterion", "start", "judge", "min_trades")
STATUSES = ("active", "judged", "yetersiz")
RESULTS = ROOT / "docs" / "fresh" / "prereg-results.csv"  # append-only: one line per judged row
RESULT_FIELDS = ["id", "judged_on", "verdict", "candidate_calmar", "baseline_calmar", "candidate_dd", "baseline_dd", "trades"]


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
    return out


def progress(row: dict, today: date, results: dict | None = None) -> str:
    res = (results or {}).get(row["id"])
    if res:
        return (f"HÜKÜM {res['judged_on']}: {res['verdict']} (Calmar {float(res['candidate_calmar']):.2f} vs "
                f"VolTarget {float(res['baseline_calmar']):.2f}, {res['trades']} işlem)")  # fmt: skip
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


def record(rows: list[dict], rid: str, cand: dict, base: dict, today: date, path: Path = RESULTS) -> str:
    """Apply the criterion, append the result line, set the row's status. Returns the verdict."""
    row = next(r for r in rows if r["id"] == rid)
    if not is_due(row, today):
        raise SystemExit(f"Refusing: {rid} is not due (judge {row['judge']}, status {row['status']}).")
    verdict = judge_row(cand, base, int(row["min_trades"]))
    new = not path.exists()
    with path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        if new:
            w.writeheader()
        w.writerow({"id": rid, "judged_on": today.isoformat(), "verdict": verdict,
                    "candidate_calmar": f"{cand['calmar']:.4f}", "baseline_calmar": f"{base['calmar']:.4f}",
                    "candidate_dd": f"{cand['max_drawdown']:.4f}", "baseline_dd": f"{base['max_drawdown']:.4f}",
                    "trades": cand["trades"]})  # fmt: skip
    row["status"] = "yetersiz" if verdict == "yetersiz" else "judged"
    return verdict


def relock(rows: list[dict], rid: str, today: date) -> None:
    row = next(r for r in rows if r["id"] == rid)
    if today >= date.fromisoformat(row["start"]):
        raise SystemExit(f"Refusing: {rid} started on {row['start']}; its criterion can no longer change.")
    row["lock"] = lock_hash(row)


def save(rows: list[dict], path: Path = FILE) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    today = datetime.now(timezone.utc).date()
    rows = load()
    if argv[:1] == ["--lock"]:
        relock(rows, argv[1], today)
        save(rows)
        print(f"{argv[1]}: locked")
        return 0
    found = problems(rows)
    for p in found:
        print("PROBLEM:", p)
    results = load_results()
    for r in rows:
        print(f"prereg {r['id']} {r['name']}: {progress(r, today, results)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
