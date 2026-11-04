"""Download market-wide BTC on-chain history for backtests (Coin Metrics Community API, no key).

    python3 scripts/onchain.py            # writes user_data/data/external/cm_btc.json + cm_stable.json

Daily, one value per UTC day:
  AdrActCnt   active addresses (sent or received that day): how many people use the network
  CapMVRVCur  MVRV = market cap / realized cap (each coin valued at the price it last moved)
  HashRate    mining power securing the network (Hash Ribbons, T158)
Market-wide on purpose (docs/research/14-coin-verisi.md): per-coin network data is not clean on the
free tier (SOL has none; BNB's history mixes its 2019 move from an ERC-20 token to its own chain).

Source: Coin Metrics Community API, https://community-api.coinmetrics.io/v4 (no key; limit 10 requests
per 6 s per IP, we send one per second). Licence: Creative Commons BY-NC (non-commercial use, credit
Coin Metrics), https://docs.coinmetrics.io/service-and-support/coverage. Fine for this research; if the
bot ever becomes a commercial product, re-check the licence.
Revision risk (research 14): address and MVRV counts come from the chain itself and are rarely
restated (unlike exchange flows). Strategies use a day's value only from the NEXT UTC day on.

Like scripts/sentiment.py and scripts/attention.py: stdlib only, output in user_data/data/ (gitignored).
"""

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "user_data" / "data" / "external" / "cm_btc.json"
BASE = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
METRICS = ["AdrActCnt", "CapMVRVCur", "HashRate"]
START = "2010-07-18"
USER_AGENT = "ft-lab-research/0.1 (crypto trading-rule research; github mertrumi-dev)"
PAUSE_S = 1.0


def first_url(start: str = START) -> str:
    q = {"assets": "btc", "metrics": ",".join(METRICS), "frequency": "1d", "start_time": start, "page_size": "10000"}
    return f"{BASE}?{urllib.parse.urlencode(q)}"


def parse(payload: dict, into: dict[str, dict[str, float]]) -> str | None:
    """Add one page's rows to {metric: {"YYYY-MM-DD": value}}; return the next page url (or None)."""
    for row in payload.get("data", []):
        day = row["time"][:10]
        for m in METRICS:
            if row.get(m) not in (None, ""):
                into.setdefault(m, {})[day] = float(row[m])
    return payload.get("next_page_url")


# T155: stablecoin supply (same API, same licence). `usdt` is all chains together (2021-06-01:
# 64.4 bn = usdt_eth 30.9 + usdt_trx 32.0 + smaller chains, checked by hand 2026-11-04).
STABLE_OUT = ROOT / "user_data" / "data" / "external" / "cm_stable.json"
STABLE_ASSETS = ["usdt", "usdc"]
STABLE_START = "2014-10-06"


def stable_url(start: str = STABLE_START) -> str:
    q = {"assets": ",".join(STABLE_ASSETS), "metrics": "SplyCur", "frequency": "1d", "start_time": start, "page_size": "10000"}
    return f"{BASE}?{urllib.parse.urlencode(q)}"


def parse_stable(payload: dict, into: dict[str, dict[str, float]]) -> str | None:
    """Add one page to {asset: {"YYYY-MM-DD": supply}}; return the next page url (or None)."""
    for row in payload.get("data", []):
        if row.get("SplyCur") not in (None, ""):
            into.setdefault(row["asset"], {})[row["time"][:10]] = float(row["SplyCur"])
    return payload.get("next_page_url")


def get(url: str) -> dict:  # pragma: no cover - network
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main() -> int:  # pragma: no cover - network
    data: dict[str, dict[str, float]] = {}
    url: str | None = first_url()
    pages = 0
    while url:
        if pages:
            time.sleep(PAUSE_S)
        url = parse(get(url), data)
        pages += 1
    if not all(data.get(m) for m in METRICS):
        print(f"missing metrics: {[m for m in METRICS if not data.get(m)]}", file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({m: dict(sorted(v.items())) for m, v in data.items()}))
    for m, v in data.items():
        print(f"{m}: {len(v)} days, {min(v)} -> {max(v)}")
    print(f"wrote {OUT.relative_to(ROOT)} ({pages} page(s))")
    stable: dict[str, dict[str, float]] = {}
    url = stable_url()
    while url:
        time.sleep(PAUSE_S)
        url = parse_stable(get(url), stable)
    if not all(stable.get(a) for a in STABLE_ASSETS):
        print(f"missing stablecoins: {[a for a in STABLE_ASSETS if not stable.get(a)]}", file=sys.stderr)
        return 1
    STABLE_OUT.write_text(json.dumps({a: dict(sorted(v.items())) for a, v in stable.items()}))
    for a, v in stable.items():
        print(f"{a} SplyCur: {len(v)} days, {min(v)} -> {max(v)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
