"""The trial freeze: no new T row or F row without Kaan's approval (stdlib only, runs on the Mac).

Frozen 2026-11-05 at N=160 (docs/journal.md). scripts/trials.py and scripts/prereg.py use this in
two places, because rows have always been added by hand as well as by command:
  - their --open command refuses without --kaan-approved "<message id or date>"
  - their check (and so the test suite) reports any row after the frozen ids with no approval line
docs/freeze-approvals.csv is the record of what was approved. It only ever grows.
"""

import csv
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APPROVALS = ROOT / "docs" / "freeze-approvals.csv"
FIELDS = ["id", "approved", "noted_on"]
FROZEN_ON = "2026-11-05"
FROZEN_N = 160
LAST_T = "T162"  # the highest id when frozen; ids are not N (REFERENCE rows and gaps)
LAST_F = "F013"
WARNING = "N=160'ta donduruldu (2026-11-05). Yeni T denemesi veya F satırı için Kaan'ın açık onayı gerekir. Onay olmadan ön kayıt bile açma."
_ROW = re.compile(r"^[TF](\d+)$")


def is_new(row_id: str) -> bool:
    """Is this id after the frozen ones? Malformed ids are the register checks' job, not ours."""
    m = _ROW.match(row_id)
    if not m:
        return False
    last = LAST_T if row_id[0] == "T" else LAST_F
    return int(m.group(1)) > int(last[1:])


def load_approvals(path: Path = APPROVALS) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open(newline="") as f:
        return {r["id"]: r["approved"] for r in csv.DictReader(f)}


def unapproved(ids: list[str], approvals: dict[str, str] | None = None) -> list[str]:
    """New ids with no approval line: a row was added around the guard."""
    approvals = load_approvals() if approvals is None else approvals
    return [i for i in ids if is_new(i) and not approvals.get(i, "").strip()]


def require_approval(approved: str | None) -> str:
    """Stop here unless a real approval was given; always show the rule."""
    print(WARNING)
    if not (approved or "").strip():
        raise SystemExit('Refusing: add --kaan-approved "<message id or date>".')
    return approved.strip()


def record(row_id: str, approved: str, today: date, path: Path = APPROVALS) -> None:
    new = not path.exists()
    with path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({"id": row_id, "approved": approved, "noted_on": today.isoformat()})
