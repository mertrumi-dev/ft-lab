"""Tests for scripts/removed.py (removed-entries diagnostic), with synthetic trade lists."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import removed  # noqa: E402


def tr(pair, when, pl=1.0):
    return {"pair": pair, "open_date": when, "profit_abs": pl, "profit_ratio": pl / 100}


def test_removed_and_added_match_on_pair_and_open_time():
    base = [tr("BTC/USDT", "2021-01-01 10:00:00+00:00"), tr("ETH/USDT", "2021-01-02 10:00:00+00:00"), tr("BTC/USDT", "2022-03-01 05:00:00")]
    cand = [tr("BTC/USDT", "2021-01-01 10:00:00+00:00", 5.0), tr("SOL/USDT", "2021-01-03 00:00:00")]
    gone, added = removed.removed_and_added(base, cand)
    assert [t["pair"] for t in gone] == ["ETH/USDT", "BTC/USDT"]  # same entry with a different P/L still counts as kept
    assert [t["pair"] for t in added] == ["SOL/USDT"]


def test_by_year_counts_trend_starts_and_skips_nan():
    nan = float("nan")
    rows = [{"year": 2020, "pl": 50.0, "pr": 0.5, "up7": 0.30, "vol30": 1.0},
            {"year": 2020, "pl": -4.0, "pr": -0.04, "up7": 0.05, "vol30": 0.8},
            {"year": 2022, "pl": -8.0, "pr": -0.08, "up7": nan, "vol30": nan}]  # fmt: skip
    y = removed.by_year(rows)
    assert [r["year"] for r in y] == [2020, 2022]
    assert y[0]["n"] == 2 and y[0]["pl"] == 46.0 and y[0]["win"] == 0.5 and y[0]["big"] == 0.5 and y[0]["vol"] == 1.0
    assert y[1]["big"] is None and y[1]["vol"] is None


def test_render_mentions_share_of_base_profit():
    rows = [{"year": 2021, "pl": 30.0, "pr": 0.3, "up7": 0.2, "vol30": 0.7}]
    text = removed.render("X vs VT", 100.0, rows, -5.0, 10, 1)
    assert "removed 1 of 10" in text and "+30% of the base profit" in text and "2021" in text and "100%" in text
    assert "base profit <= 0" in removed.render("X", -1.0, rows, 0.0, 1, 0)
