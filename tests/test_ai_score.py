"""Tests for scripts/ai_score.py with a fake views file and fake closes."""

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import ai_score  # noqa: E402

VIEWS = """# AI
| Tarih (son mum) | Coin | Kapanış | Yorum | 7 gün tahmini | Güven | Gerçekleşen (7g) | İsabet |
|---|---|---|---|---|---|---|---|
| 2026-10-31 | BTC | 100 | düşüş var | aşağı | 1 | | |
| 2026-10-31 | ETH | 100 | yatay | yatay | 2 | | |
| 2026-10-31 | SOL | 100 | x | yukarı | 3 | | |
| 2026-11-05 | BNB | 100 | y | aşağı | 1 | | |
"""
CLOSES = {("BTC", date(2026, 11, 7)): 95.0, ("ETH", date(2026, 11, 7)): 101.0, ("SOL", date(2026, 11, 7)): 99.0}


def close_on(coin, day):
    return CLOSES.get((coin, day))


def test_parse_views():
    v = ai_score.parse_views(VIEWS)
    assert [x["coin"] for x in v] == ["BTC", "ETH", "SOL", "BNB"] and v[2]["confidence"] == 3


def test_nothing_due_today():
    rows = ai_score.score(ai_score.parse_views(VIEWS), close_on, date(2026, 11, 1))
    t = ai_score.totals(rows)
    assert t["n"] == 0 and t["next_due"] == "2026-11-07"
    assert "henüz puanlanacak tahmin yok (ilk: 2026-11-08, 2026-11-07 kapanışıyla)" in ai_score.render(t)


def test_scoring_after_horizon():
    rows = ai_score.score(ai_score.parse_views(VIEWS), close_on, date(2026, 11, 8))
    done = {r["coin"]: r for r in rows if r["hit"] != ""}
    assert done["BTC"]["actual"] == "aşağı" and done["BTC"]["hit"] == 1  # -5%
    assert done["ETH"]["actual"] == "yatay" and done["ETH"]["hit"] == 1  # +1% inside ±2%
    assert done["SOL"]["actual"] == "yatay" and done["SOL"]["hit"] == 0  # called up, moved -1%
    t = ai_score.totals(rows)
    assert t["n"] == 3 and t["hits"] == 2 and t["pending"] == 1 and t["always_up"] == 0
    assert t["p_value"] == pytest.approx(ai_score.binom_p_at_least(2, 3))


def test_binomial_and_idempotent_csv(tmp_path):
    assert ai_score.binom_p_at_least(0, 5) == pytest.approx(1.0)
    assert ai_score.binom_p_at_least(5, 5) == pytest.approx((1 / 3) ** 5)
    rows = ai_score.score(ai_score.parse_views(VIEWS), close_on, date(2026, 11, 8))
    p = tmp_path / "s.csv"
    ai_score.write_csv(p, rows)
    first = p.read_text()
    ai_score.write_csv(p, rows)
    assert p.read_text() == first and first.count("\n") == 5


def test_rules_constants_match_the_file():
    text = (Path(__file__).resolve().parent.parent / "docs" / "fresh" / "ai-views.md").read_text()
    assert "7 gün" in text and "±%2" in text
    assert ai_score.HORIZON == 7 and ai_score.FLAT_BAND == 0.02
