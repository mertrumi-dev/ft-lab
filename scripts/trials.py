"""The trial register: docs/trials.csv, one row per trial ever run (stdlib only, runs on the Mac).

    python3 scripts/trials.py            # check the file, print the counts
    python3 scripts/trials.py --find adx # was this idea already tried? (trials.csv + docs/journal.md)
    python3 scripts/trials.py --open --kaan-approved "<message id or date>" --name X --family F --idea I --criterion C
                                         # new row, PENDING. Frozen: refused without the approval (scripts/freeze.py)

Rules checked:
  - ids are unique (T001, T002, ...)
  - verdict is one of VERDICTS
  - the three Calmar columns are a number or blank (blank = not measured / not recorded)
  - every strategy name that docs/experiments.md says was backtested appears as a row
  - no row after the frozen ids without an approval line (scripts/freeze.py)

N for the Deflated Sharpe Ratio (scripts/deflated.py) = every row except REFERENCE rows
(neighbours count: each one was a real look at the data).
"""

import argparse
import csv
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import freeze  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TRIALS = ROOT / "docs" / "trials.csv"
EXPERIMENTS = ROOT / "docs" / "experiments.md"
FIELDS = ["id", "date", "name", "family", "idea", "criterion", "verdict",
          "train_core_calmar", "validation_core_calmar", "early_calmar", "slices", "notes"]  # fmt: skip
# PASS: passed its pre-registered criterion. FAIL: did not. WATCH: failed or unproven, but followed
# on fresh data. ELIMINATED: dropped on train without reaching a formal test. NEIGHBOUR: a robustness
# variant (never a candidate). REFERENCE: someone else's bot, comparison only (not a trial).
# PENDING: pre-registered, not run yet (it already counts in N: the decision to test was made).
VERDICTS = ("PASS", "FAIL", "WATCH", "ELIMINATED", "NEIGHBOUR", "REFERENCE", "PENDING")
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
    out += [f"{i}: opened after the freeze with no approval line: {freeze.WARNING}" for i in freeze.unapproved([r["id"] for r in rows])]
    return out


def counts(rows: list[dict]) -> Counter:
    return Counter(r["verdict"] for r in rows)


def n_trials(rows: list[dict]) -> int:
    """N for the Deflated Sharpe Ratio: every look at the data except other people's bots."""
    return sum(r["verdict"] != "REFERENCE" for r in rows)


# The same idea is written with different words (2026-11-02: "relative strength" T150 was a
# near-copy of "kesitsel momentum / üst yarı" T107 and a plain keyword search missed it).
# A search word also matches the other words of its group. Turkish + English, lower case.
SYNONYMS = [
    ("momentum", "strength", "güç", "relative", "göreli", "rank", "sıra", "üst yarı", "top half", "kesitsel", "cross-sectional"),
    ("stop", "stoploss", "zarar durdur"),
    ("volume", "hacim", "obv"),
    ("weekend", "hafta sonu", "cumartesi", "pazar", "saturday", "sunday"),
    ("exit", "çıkış"),
    ("fear", "korku", "fng", "greed", "açgözlü"),
    ("volatility", "oynaklık", "atr"),
    ("breadth", "genişlik"),
    ("attention", "ilgi", "wikipedia", "pageview"),
    ("partial", "kısmi", "yarım", "take profit", "kâr al"),
    ("cooldown", "bekleme", "kilit", "lock"),
]  # fmt: skip


def alternatives(word: str) -> tuple[str, ...]:
    """The word and its synonyms (the word alone if it is in no group)."""
    w = word.lower()
    for group in SYNONYMS:
        if w in group:
            return group
    return (w,)


def find(rows: list[dict], journal_text: str, words: list[str]) -> list[str]:
    """Rows and journal lines mentioning ALL the words, each word or one of its synonyms
    (case-insensitive): check before pre-registering."""
    alts = [alternatives(w) for w in words]

    def match(text: str) -> bool:
        low = text.lower()
        return all(any(a in low for a in group) for group in alts)

    hits = [f"{r['id']} {r['verdict']:<10} {r['name']}: {r['idea'][:90]}" for r in rows
            if match(" ".join((r["name"], r["idea"], r["notes"])))]  # fmt: skip
    hits += [f"journal: {ln.strip()[:160]}" for ln in journal_text.splitlines() if match(ln)]
    return hits


def next_id(rows: list[dict]) -> str:
    return f"T{max(int(r['id'][1:]) for r in rows) + 1:03d}"


def open_row(argv: list[str], path: Path = TRIALS, approvals_path: Path = freeze.APPROVALS) -> str:
    """Pre-register one new trial (verdict PENDING: it counts in N from now on). Returns its id."""
    p = argparse.ArgumentParser(prog="trials.py --open")
    p.add_argument("--kaan-approved")
    for field in ("name", "family", "idea", "criterion"):
        p.add_argument(f"--{field}")
    a = p.parse_args(argv)
    approved = freeze.require_approval(a.kaan_approved)  # the refusal comes before anything else is asked
    if not all((a.name, a.family, a.idea, a.criterion)):
        raise SystemExit("Refusing: --name, --family, --idea and --criterion are all needed.")
    rows = load(path)
    today = datetime.now(timezone.utc).date()
    rid = next_id(rows)
    freeze.record(rid, approved, today, approvals_path)
    with path.open("a", newline="") as f:
        csv.DictWriter(f, fieldnames=FIELDS).writerow({**dict.fromkeys(FIELDS, ""), "id": rid, "date": today.isoformat(), "name": a.name,
                                                       "family": a.family, "idea": a.idea, "criterion": a.criterion, "verdict": "PENDING"})  # fmt: skip
    return rid


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["--open"]:
        print(f"{open_row(argv[1:])}: opened, PENDING")
        return 0
    rows = load()
    if argv[:1] == ["--find"]:
        journal = ROOT / "docs" / "journal.md"
        used = [g for g in (alternatives(w) for w in argv[1:]) if len(g) > 1]
        if used:
            print("also searched (synonyms): " + "; ".join(", ".join(g) for g in used))
        hits = find(rows, journal.read_text() if journal.exists() else "", argv[1:])
        print("\n".join(hits) if hits else f"nothing found for {' '.join(argv[1:])!r}")
        return 0
    found = problems(rows, tested_names(EXPERIMENTS.read_text()) if EXPERIMENTS.exists() else set())
    for p in found:
        print("PROBLEM:", p)
    c = counts(rows)
    print(f"trials.csv: {len(rows)} rows | " + ", ".join(f"{v} {c[v]}" for v in VERDICTS) + f" | DSR N = {n_trials(rows)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
