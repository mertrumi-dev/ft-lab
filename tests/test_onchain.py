"""Tests for scripts/onchain.py (Coin Metrics fetcher; no network here)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import onchain  # noqa: E402


def test_first_url_asks_btc_daily_both_metrics_without_a_key():
    u = onchain.first_url()
    assert "assets=btc" in u and "frequency=1d" in u and "AdrActCnt%2CCapMVRVCur" in u and "api_key" not in u


def test_parse_pages_and_skips_empty_values():
    into = {}
    nxt = onchain.parse({"data": [{"time": "2018-06-01T00:00:00.000000000Z", "AdrActCnt": "683588", "CapMVRVCur": "1.9"},
                                  {"time": "2018-06-02T00:00:00.000000000Z", "AdrActCnt": "700000"}],
                         "next_page_url": "https://x/next"}, into)  # fmt: skip
    assert nxt == "https://x/next"
    assert into == {"AdrActCnt": {"2018-06-01": 683588.0, "2018-06-02": 700000.0}, "CapMVRVCur": {"2018-06-01": 1.9}}
    assert onchain.parse({"data": []}, into) is None


def test_output_is_gitignored_and_licence_is_named():
    assert onchain.OUT.relative_to(onchain.ROOT).parts[:2] == ("user_data", "data")
    assert "BY-NC" in onchain.__doc__ and onchain.PAUSE_S >= 0.6  # 10 requests / 6 s limit


def test_stable_url_and_parse():
    u = onchain.stable_url()
    assert "assets=usdt%2Cusdc" in u and "metrics=SplyCur" in u and "api_key" not in u
    into = {}
    nxt = onchain.parse_stable({"data": [{"asset": "usdt", "time": "2021-06-01T00:00:00.000000000Z", "SplyCur": "64.4"},
                                         {"asset": "usdc", "time": "2021-06-01T00:00:00.000000000Z"}]}, into)  # fmt: skip
    assert nxt is None and into == {"usdt": {"2021-06-01": 64.4}}
    assert onchain.STABLE_OUT.relative_to(onchain.ROOT).parts[:2] == ("user_data", "data")
