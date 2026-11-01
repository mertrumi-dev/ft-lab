"""Tests for scripts/kaan_report.py (rendering with fake inputs)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import kaan_report  # noqa: E402

SCAN = """pair         state                            vs EMA200      30d  size
STX/USDT     in trend                             +3.9%   -12.4%   38%
BTC/USDT     below EMA200                         -1.9%   -10.3%  100% *
ETH/USDT     above EMA200, short trend down       +0.5%   -17.9%  100% *
"""
BOTS = """Famous bot types vs our rule, --timerange 20261001-20261102, universe core
Bot                      Trades    Return     CAGR   MaxDD  Calmar
Buy & hold                    -    -13.5%   -82.8%   17.3%   -4.78
Grid bot (Pionex-style)      83     -3.9%   -38.0%    6.1%   -6.24
TrendEma                     17     -3.4%   -34.0%    3.8%   -9.05  <50 trades
TrendEmaVolTarget            17     -3.3%   -33.3%    3.7%   -9.08  <50 trades
Year by year                        2026
TrendEma                    -3.4% DD  4%
"""


def test_core_scan_rows_only_bot_coins():
    rows = kaan_report.core_scan_rows(SCAN)
    assert [r["pair"] for r in rows] == ["BTC/USDT", "ETH/USDT"]
    assert rows[1]["state"] == "above EMA200, short trend down" and rows[0]["size"] == "100%"


def test_bots_rows_keep_first_table_only():
    rows = kaan_report.bots_rows(BOTS)
    assert rows[0].startswith("Buy & hold") and any(r.startswith("TrendEmaVolTarget ") for r in rows)
    assert not any("DD  4%" in r for r in rows)


def test_ai_counts(tmp_path):
    p = tmp_path / "ai.md"
    p.write_text("| Tarih | ... |\n|---|---|\n| 2026-10-31 | BTC | 1 | x | aşağı | 1 | | |\n| 2026-10-31 | ETH | 2 | y | aşağı | 2 | -3% | evet |\n")
    assert kaan_report.ai_counts(p) == (2, 1)


def test_render_and_write(tmp_path):
    b = tmp_path / "b.csv"
    b.write_text("date,n_coins,breadth,n_in_trend,n_entry_now,BTC,ETH,SOL,BNB,XRP\n2026-11-01,61,0.131,8,0,below,below,below,below,below\n")
    text = kaan_report.render("2026-11-02", {"status": "ft-lab Up", "other_errors": 0, "network_errors": 5, "open": 0,
                                             "closed": 0, "profit": 0.0, "drawdown": 0.0, "phase0": "PASS"},
                              SCAN, kaan_report.breadth_rows(b), BOTS, "", "x: no orders yet", (5, 0))
    for must in ("## 1. Bot sağlığı", "EMA200 altında (bekliyor)", "%13", "TrendEmaVolTarget", "no orders yet", "Kaydedilen yorum: 5"):
        assert must in text
    path = kaan_report.write(tmp_path, "2026-11-02", text)
    assert path.name == "report-2026-11-02.md" and (tmp_path / "latest.md").read_text() == text


def test_daily_plan_has_execution_step():
    import daily

    titles = [t for t, _, _ in daily.plan(False, True)]
    assert "execution" in titles and titles[-1] == "scan pool"


def test_tidy_row_aligns_long_names_and_header_present():
    row = "TSMOM (ours, daily, vol-scaled)      7     -7.7%   -62.3%   11.7%   -5.33  <50 trades"
    t = kaan_report.tidy_bots_row(row)
    assert t.startswith("TSMOM (ours, daily, vol-scaled)") and t.endswith("<50 işlem")
    assert len(t.split("<50")[0].rstrip()) == len(kaan_report.TABLE_HEAD)
    text = kaan_report.render("d", {"longest_gap": "2.0h", "network_peak": "2026-10-31 18:00 UTC'de 145"}, "", [], BOTS, "", "", (0, 0))
    assert kaan_report.TABLE_HEAD in text and "En uzun bağlantısız süre: 2.0h" in text and "en çok" in text


def test_expected_line_shown():
    text = kaan_report.render("d", {}, "", [], BOTS, "", "", (0, 0),
                              "x\nexpected_line: 31 gün, getiri -3.3% (beklenen aralık) -> beklenen aralıkta\n")
    assert "VolTarget beklenen aralıkta mı? 31 gün" in text


def test_section_7_trades():
    text = kaan_report.render("d", {}, "", [], BOTS, "", "", (0, 0), "", "# İşlem açıklamaları\n\nSahte para...\n\nHenüz işlem yok.\n- BTC: x\n")
    assert "## 7. İşlemler (sade dille)" in text and "Henüz işlem yok." in text and "- BTC: x" in text


def test_ai_score_line_in_section_6():
    text = kaan_report.render("d", {}, "", [], BOTS, "", "", (5, 0), "", "",
                              "ai_score: henüz puanlanacak tahmin yok (ilk: 2026-11-07), bekleyen 5\n")
    assert "- Puanlama: henüz puanlanacak tahmin yok" in text
