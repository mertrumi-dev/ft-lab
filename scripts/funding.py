"""Download Binance perpetual FUNDING RATE history for backtests (read-only public data, no key).

    python3 scripts/funding.py            # writes user_data/data/external/funding_<COIN>.json

We trade SPOT only; the funding rate is only READ as a crowding signal. Every 8 hours, perpetual-
futures longs pay shorts the funding rate (or the reverse when it is negative). A high positive
rate means many traders hold leveraged longs: the market is "crowded" on the long side.

Source: Binance USD-M futures public endpoint GET https://fapi.binance.com/fapi/v1/fundingRate
(symbol, startTime, limit 1000; no key; we pause between calls). Each record: fundingTime (ms,
the moment the rate is settled and known) and fundingRate. Binance's open-interest history only
reaches back ~30 days, so it is not downloaded (not usable in backtests).

Coins: the 5 core coins and the 2018 "early" coins. A coin without perpetuals gets no file and
the strategy's filter stays off for it. Like scripts/sentiment.py: stdlib only, output in
user_data/data/ (gitignored). Strategies use a rate only from its fundingTime on.
"""

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "user_data" / "data" / "external"
URL = "https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&startTime={start}&limit=1000"
CORE_EARLY = ["BTC", "ETH", "SOL", "BNB", "XRP", "LTC", "ADA", "NEO", "EOS", "XLM", "TRX", "ETC", "QTUM", "IOTA"]
# the 2024 listings (alt2024b): without their rates the filter would be off there and the trial
# would compare identical trades on the new-coin judge
ALT2024B = ["AI", "XAI", "MANTA", "ALT", "JUP", "DYM", "PIXEL", "STRK", "PORTAL", "WIF", "AEVO", "BOME", "ETHFI",
            "ENA", "W", "TNSR", "SAGA", "OMNI", "REZ", "BB", "NOT", "IO", "ZK", "ZRO"]  # fmt: skip
COINS = CORE_EARLY + ALT2024B
FIRST_MS = 1_546_300_800_000  # 2019-01-01: before Binance's first perpetual (BTCUSDT, 2019-09)
USER_AGENT = "ft-lab-research/0.1 (crypto trading-rule research; github mertrumi-dev)"
PAUSE_S = 1.0


def out_path(coin: str) -> Path:
    return OUT_DIR / f"funding_{coin}.json"


def parse(rows: list[dict]) -> dict[int, float]:
    """API rows -> {fundingTime ms: rate}."""
    return {int(r["fundingTime"]): float(r["fundingRate"]) for r in rows if r.get("fundingRate") not in (None, "")}


def next_start(rows: list[dict]) -> int | None:
    """The startTime for the next page, or None when this page was the last (fewer than 1000 rows)."""
    if len(rows) < 1000:
        return None
    return max(int(r["fundingTime"]) for r in rows) + 1


def get(symbol: str, start: int) -> list[dict]:  # pragma: no cover - network
    req = urllib.request.Request(URL.format(symbol=symbol, start=start), headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch(coin: str) -> dict[int, float]:  # pragma: no cover - network
    data: dict[int, float] = {}
    start: int | None = FIRST_MS
    while start is not None:
        try:
            rows = get(f"{coin}USDT", start)
        except urllib.error.HTTPError as e:
            if e.code == 400:  # no such perpetual
                return {}
            raise
        data.update(parse(rows))
        start = next_start(rows)
        time.sleep(PAUSE_S)
    return data


def main() -> int:  # pragma: no cover - network
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    from datetime import datetime, timezone

    for coin in COINS:
        data = fetch(coin)
        if not data:
            print(f"{coin}: no perpetual funding data")
            continue
        out_path(coin).write_text(json.dumps({str(k): v for k, v in sorted(data.items())}))
        first = datetime.fromtimestamp(min(data) / 1000, timezone.utc)
        last = datetime.fromtimestamp(max(data) / 1000, timezone.utc)
        print(f"{coin}: {len(data)} rates, {first:%Y-%m-%d} -> {last:%Y-%m-%d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
