"""Tests for scripts/attention.py (Wikipedia pageviews fetcher; no network here)."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import attention  # noqa: E402


def test_year_ranges_clip_to_first_and_last_day():
    r = attention.year_ranges(date(2015, 7, 1), date(2017, 3, 5))
    assert r == [("20150701", "20151231"), ("20160101", "20161231"), ("20170101", "20170305")]


def test_parse_api_items():
    payload = {"items": [{"timestamp": "2015070100", "views": 12957}, {"timestamp": "2015070200", "views": 9802}]}
    assert attention.parse(payload) == {"2015-07-01": 12957, "2015-07-02": 9802}
    assert attention.parse({}) == {}


def test_polite_waits():
    assert attention.PAUSE_S >= 5
    assert attention.wait_after_429("30", 0) == 30.0
    assert attention.wait_after_429(None, 0) == 60.0 and attention.wait_after_429("x", 2) == 240.0


def test_output_is_gitignored_data():
    assert attention.OUT.relative_to(attention.ROOT).parts[:2] == ("user_data", "data")
    assert "user_data/data/*" in (attention.ROOT / ".gitignore").read_text().splitlines()
