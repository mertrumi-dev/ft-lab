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


def progress(row: dict, today: date) -> str:
    start, judge = date.fromisoformat(row["start"]), date.fromisoformat(row["judge"])
    total = (judge - start).days
    if today < start:
        return f"başlamadı (başlangıç {start}, hüküm {judge})"
    done = min((today - start).days, total)
    if today < judge:
        return f"henüz hüküm yok ({done}/{total} gün)"
    return f"hüküm günü geldi ({total}/{total} gün): değerlendir, en az {row['min_trades']} işlem yoksa 'yetersiz'"


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
    for r in rows:
        print(f"prereg {r['id']} {r['name']}: {progress(r, today)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
