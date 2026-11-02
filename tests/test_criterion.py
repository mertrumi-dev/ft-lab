"""Tests for scripts/criterion.py (the standard trial verdict), with tonight's real numbers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import criterion  # noqa: E402


def m(calmar, dd=0.10, trades=300):
    return {"calmar": calmar, "max_drawdown": dd, "trades": trades}


VT = {"train": m(1.86, 0.132, 638), "validation": m(1.93, 0.130, 217), "window24": m(-0.46, 0.146, 382), "early": m(2.46, 0.096, 696)}
VOTE9 = {"train": m(1.73, 0.138, 632), "validation": m(2.18, 0.134, 212), "window24": m(-0.22, 0.139, 385), "early": m(2.57, 0.090, 680)}


def test_vote9_passes_t110_like_the_journal():
    v = criterion.verdict(VOTE9, VT)
    assert v["t110_pass"] and v["robust"] is None
    assert criterion.summary(v) == "PASS"


def test_t114_volconfirm_fails_only_alt2024b():
    vc = {"train": m(2.06, 0.077, 463), "validation": m(2.68, 0.087, 153), "window24": m(-0.53, 0.160, 321), "early": m(2.36, 0.091, 562)}
    v = criterion.verdict(vc, VT)
    assert not v["t110_pass"]
    assert [n for n, ok, _ in v["t110"] if not ok] == ["alt2024b/window24"]
    assert criterion.summary(v) == "FAIL (alt2024b/window24)"


def test_drawdown_counts_on_alt2024b_and_trades_minimum():
    better_calmar_worse_dd = {**VOTE9, "window24": m(-0.40, 0.150, 380)}
    assert not criterion.verdict(better_calmar_worse_dd, VT)["t110_pass"]
    few = {**VOTE9, "early": m(2.57, 0.090, 49)}
    v = criterion.verdict(few, VT)
    assert not v["t110_pass"] and "early" in criterion.summary(v) or "50" in criterion.summary(v)


def test_missing_case_is_a_fail_not_a_pass():
    v = criterion.verdict({k: x for k, x in VOTE9.items() if k != "validation"}, VT)
    assert not v["t110_pass"]


def test_vote9_robustness_fails_like_the_journal():
    neighbours = {"VTVote4x2": {"train": m(1.07), "window24": m(-0.44), "early": m(1.93)},
                  "VTVote6x4": {"train": m(1.90), "window24": m(-0.37), "early": m(2.31)}}  # fmt: skip
    fee_c = {"window24": m(-0.50), "early": m(1.35)}
    fee_b = {"window24": m(-0.67), "early": m(1.49)}
    v = criterion.verdict(VOTE9, VT, neighbours, fee_c, fee_b)
    assert v["t110_pass"] and v["robust"] is False
    # the coded standard (train >= 0.90x, alt2024b >, early >= 0.90x) lets 6/4 pass (early 2.31 >= 2.21);
    # Vote9's own pre-registration was stricter (early > 2.46). Same outcome: 4/2 and fee x2 still fail.
    assert v["plateau"]["VTVote4x2"][0] is False and v["plateau"]["VTVote6x4"][0] is True
    assert [ok for _, ok, _ in v["fee"]] == [True, False]
    assert criterion.summary(v) == "PASS; sağlamlık TUTMADI"


def test_robust_needs_every_neighbour_and_both_fee_cases():
    good = {"train": m(1.80), "window24": m(-0.30), "early": m(2.40)}
    fee_c, fee_b = {"window24": m(-0.5), "early": m(1.6)}, {"window24": m(-0.67), "early": m(1.49)}
    assert criterion.verdict(VOTE9, VT, {"A": good, "B": good}, fee_c, fee_b)["robust"] is True
    assert criterion.verdict(VOTE9, VT, {}, fee_c, fee_b)["robust"] is False  # no neighbours = not shown robust


def test_render_mentions_every_check():
    text = criterion.render(criterion.verdict(VOTE9, VT), "TrendEmaVolTargetVote9", "TrendEmaVolTarget")
    for word in ("train core", "validation core", "alt2024b/window24", "early", "SONUÇ: PASS"):
        assert word in text
