"""The trial register: docs/trials.csv, one row per trial ever run (stdlib only, runs on the Mac).

    python3 scripts/trials.py            # check the file, print the counts

Rules checked:
  - ids are unique (T001, T002, ...)
  - verdict is one of VERDICTS
  - the three Calmar columns are a number or blank (blank = not measured / not recorded)
  - every strategy name that docs/experiments.md says was backtested appears as a row

N for the Deflated Sharpe Ratio (scripts/deflated.py) = every row except REFERENCE rows
(neighbours count: each one was a real look at the data).
"""

import csv
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRIALS = ROOT / "docs" / "trials.csv"
EXPERIMENTS = ROOT / "docs" / "experiments.md"
FIELDS = ["id", "date", "name", "family", "idea", "criterion", "verdict",
          "train_core_calmar", "validation_core_calmar", "early_calmar", "slices", "notes"]  # fmt: skip
# PASS: passed its pre-registered criterion. FAIL: did not. WATCH: failed or unproven, but followed
# on fresh data. ELIMINATED: dropped on train without reaching a formal test. NEIGHBOUR: a robustness
# variant (never a candidate). REFERENCE: someone else's bot, comparison only (not a trial).
VERDICTS = ("PASS", "FAIL", "WATCH", "ELIMINATED", "NEIGHBOUR", "REFERENCE")
NUMBERS = ("train_core_calmar", "validation_core_calmar", "early_calmar")
ID = re.compile(r"^T\d{3}$")


def load(path: Path = TRIALS) -> list[dict]:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != FIELDS:
            raise ValueError(f"columns must be {FIELDS}, got {reader.fieldnames}")
        return list(reader)


def tested_names(experiments_text: str) -> set[str]:
    """Strategy names in the 'Strateji' column of docs/experiments.md (comma separated)."""
    names = set()
    for line in experiments_text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and re.match(r"^\d{4}-\d{2}-\d{2}", cells[0]):
            names.update(n.strip() for n in cells[2].split(",") if n.strip())
    return names


def problems(rows: list[dict], tested: set[str]) -> list[str]:
    out = []
    ids = Counter(r["id"] for r in rows)
    out += [f"duplicate id {i}" for i, n in ids.items() if n > 1]
    for r in rows:
        if not ID.match(r["id"]):
            out.append(f"{r['id']}: id must look like T001")
        if r["verdict"] not in VERDICTS:
            out.append(f"{r['id']} {r['name']}: verdict {r['verdict']!r} not in {VERDICTS}")
        for col in NUMBERS:
            if r[col]:
                try:
                    float(r[col])
                except ValueError:
                    out.append(f"{r['id']} {r['name']}: {col} {r[col]!r} is not a number")
    names = {r["name"] for r in rows}
    out += [f"backtested but missing from trials.csv: {n}" for n in sorted(tested - names)]
    return out


def counts(rows: list[dict]) -> Counter:
    return Counter(r["verdict"] for r in rows)


def n_trials(rows: list[dict]) -> int:
    """N for the Deflated Sharpe Ratio: every look at the data except other people's bots."""
    return sum(r["verdict"] != "REFERENCE" for r in rows)


def main() -> int:
    rows = load()
    found = problems(rows, tested_names(EXPERIMENTS.read_text()) if EXPERIMENTS.exists() else set())
    for p in found:
        print("PROBLEM:", p)
    c = counts(rows)
    print(f"trials.csv: {len(rows)} rows | " + ", ".join(f"{v} {c[v]}" for v in VERDICTS) + f" | DSR N = {n_trials(rows)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
