"""Tests for scripts/funding.py (no network)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import funding  # noqa: E402


def test_parse_and_paging():
    rows = [{"fundingTime": 1000, "fundingRate": "0.0001"}, {"fundingTime": 2000, "fundingRate": "-0.0002"}]
    assert funding.parse(rows) == {1000: 0.0001, 2000: -0.0002}
    assert funding.next_start(rows) is None  # a short page is the last one
    assert funding.next_start([{"fundingTime": i, "fundingRate": "0"} for i in range(1000)]) == 1000


def test_coins_and_output_location():
    assert {"BTC", "SOL", "IOTA", "ZRO"} <= set(funding.COINS)
    assert funding.out_path("BTC").relative_to(funding.ROOT).parts[:2] == ("user_data", "data")
