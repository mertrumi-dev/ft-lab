"""The standard trial verdict (T110+ criterion + robustness reading), as code. Stdlib only.

Input: measured numbers per case, e.g. {"train": {"calmar": 1.8, "max_drawdown": 0.13, "trades": 600}, ...}
Output: a list of (check, ok, text) and an overall verdict. scripts/verdict.py measures the numbers
from backtest results (same equity curve as `ft.py bots`); this module only judges them.

The rules (docs/journal.md, 2026-11-01 21:20 UTC and the robustness protocol used since):
  T110+, candidate vs baseline (kill switch off, fee 0.0015):
    train core      Calmar >= 0.90 x baseline
    validation core Calmar >= baseline
    alt2024b        Calmar >  baseline AND max drawdown not higher
    early           Calmar >= 0.90 x baseline
    every case      >= 50 trades
  Robustness (only meaningful after a T110+ PASS):
    plateau: EVERY neighbour has train >= 0.90 x, alt2024b Calmar > baseline and early >= 0.90 x
    fee x2:  candidate Calmar > baseline at 2x fee on alt2024b AND early
"""

CASES = [("train", "core"), ("validation", "core"), ("window24", "alt2024b"), ("early", "early")]
NEIGHBOUR_CASES = [("train", "core"), ("window24", "alt2024b"), ("early", "early")]
FEE_CASES = [("window24", "alt2024b"), ("early", "early")]
MIN_TRADES = 50
SHARE = 0.90


def t110_checks(cand: dict, base: dict) -> list[tuple[str, bool, str]]:
    """cand/base: {slice_name: {"calmar", "max_drawdown", "trades"}}; a missing case fails its check."""
    out = []

    def have(name):
        return name in cand and name in base

    if have("train"):
        c, b = cand["train"]["calmar"], base["train"]["calmar"]
        out.append(("train core", c >= SHARE * b, f"{c:.2f} vs {b:.2f} (sınır {SHARE * b:.2f})"))
    else:
        out.append(("train core", False, "sonuç yok"))
    if have("validation"):
        c, b = cand["validation"]["calmar"], base["validation"]["calmar"]
        out.append(("validation core", c >= b, f"{c:.2f} vs {b:.2f}"))
    else:
        out.append(("validation core", False, "sonuç yok"))
    if have("window24"):
        c, b = cand["window24"], base["window24"]
        ok = c["calmar"] > b["calmar"] and c["max_drawdown"] <= b["max_drawdown"]
        out.append(("alt2024b/window24", ok, f"{c['calmar']:.2f} vs {b['calmar']:.2f}, "
                                            f"DD %{c['max_drawdown'] * 100:.1f} vs %{b['max_drawdown'] * 100:.1f}"))  # fmt: skip
    else:
        out.append(("alt2024b/window24", False, "sonuç yok"))
    if have("early"):
        c, b = cand["early"]["calmar"], base["early"]["calmar"]
        out.append(("early", c >= SHARE * b, f"{c:.2f} vs {b:.2f} (sınır {SHARE * b:.2f})"))
    else:
        out.append(("early", False, "sonuç yok"))
    few = [name for name, m in cand.items() if (m.get("trades") or 0) < MIN_TRADES]
    out.append((f">= {MIN_TRADES} işlem", not few, "hepsi yeterli" if not few else f"az: {', '.join(sorted(few))}"))
    return out


def neighbour_ok(n: dict, base: dict) -> tuple[bool, str]:
    """One neighbour on the plateau? train >= 0.90x, alt2024b Calmar > baseline, early >= 0.90x."""
    parts, ok = [], True
    for name, rule in (("train", "share"), ("window24", "above"), ("early", "share")):
        if name not in n or name not in base:
            return False, f"{name}: sonuç yok"
        c, b = n[name]["calmar"], base[name]["calmar"]
        good = c > b if rule == "above" else c >= SHARE * b
        ok &= good
        parts.append(f"{name} {c:.2f}{'✓' if good else '✗'}")
    return ok, ", ".join(parts)


def fee_checks(cand_fee: dict, base_fee: dict) -> list[tuple[str, bool, str]]:
    out = []
    for name, _ in FEE_CASES:
        if name not in cand_fee or name not in base_fee:
            out.append((f"2x komisyon {name}", False, "sonuç yok"))
            continue
        c, b = cand_fee[name]["calmar"], base_fee[name]["calmar"]
        out.append((f"2x komisyon {name}", c > b, f"{c:.2f} vs {b:.2f}"))
    return out


def verdict(cand: dict, base: dict, neighbours: dict | None = None, cand_fee: dict | None = None,
            base_fee: dict | None = None) -> dict:  # fmt: skip
    """Everything in one place: T110+ checks, then (if given) the plateau and fee x2 readings."""
    checks = t110_checks(cand, base)
    passed = all(ok for _, ok, _ in checks)
    out = {"t110": checks, "t110_pass": passed, "plateau": None, "fee": None, "robust": None}
    if neighbours is not None:
        rows = {name: neighbour_ok(n, base) for name, n in neighbours.items()}
        out["plateau"] = rows
    if cand_fee is not None and base_fee is not None:
        out["fee"] = fee_checks(cand_fee, base_fee)
    if out["plateau"] is not None and out["fee"] is not None:
        out["robust"] = bool(rows) and all(ok for ok, _ in rows.values()) and all(ok for _, ok, _ in out["fee"])
    return out


def summary(v: dict) -> str:
    """One Turkish line for the journal: PASS/FAIL and, if measured, the robustness outcome."""
    head = "PASS" if v["t110_pass"] else "FAIL"
    failed = [name for name, ok, _ in v["t110"] if not ok]
    line = head + ("" if not failed else f" ({', '.join(failed)})")
    if v["robust"] is not None:
        line += "; sağlam" if v["robust"] else "; sağlamlık TUTMADI"
    return line


def render(v: dict, candidate: str, baseline: str) -> str:
    lines = [f"Verdict: {candidate} vs {baseline} (T110+ ölçütü, kill switch kapalı)"]
    lines += [f"  {'✓' if ok else '✗'} {name}: {text}" for name, ok, text in v["t110"]]
    if v["plateau"] is not None:
        lines.append("Plato (komşular):")
        lines += [f"  {'✓' if ok else '✗'} {name}: {text}" for name, (ok, text) in v["plateau"].items()]
    if v["fee"] is not None:
        lines.append("2 kat komisyon:")
        lines += [f"  {'✓' if ok else '✗'} {name}: {text}" for name, ok, text in v["fee"]]
    lines.append("SONUÇ: " + summary(v))
    return "\n".join(lines)
