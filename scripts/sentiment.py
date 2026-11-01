"""Download the Crypto Fear & Greed Index history (alternative.me) for backtests.

The index is one number per day, 0-100, built from volatility, volume, social
media, Bitcoin dominance and search trends. Low = people are scared, high =
people are greedy. It is the closest thing to "the news mood" that has a long,
free, day-by-day history, so it can be backtested honestly.

    python3 scripts/sentiment.py            # writes user_data/data/fear_greed.json

Stdlib only, so it runs on the Mac without pandas/freqtrade. The output file is
in user_data/data/, which is gitignored (it is data, not code).
Source: https://alternative.me/crypto/fear-and-greed-index/ (free API, attribution requested).
"""

import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "user_data" / "data" / "fear_greed.json"
URL = "https://api.alternative.me/fng/?limit=0&format=json"


def parse(payload: dict) -> dict[str, int]:
    """API answer -> {"YYYY-MM-DD": value}, dates in UTC, oldest first."""
    days = {}
    for row in payload["data"]:
        day = datetime.fromtimestamp(int(row["timestamp"]), tz=timezone.utc).strftime("%Y-%m-%d")
        days[day] = int(row["value"])
    return dict(sorted(days.items()))


def main() -> int:
    with urllib.request.urlopen(URL, timeout=30) as resp:
        payload = json.load(resp)
    days = parse(payload)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(days, indent=0))
    first, last = next(iter(days)), next(reversed(days))
    print(f"{len(days)} days, {first} .. {last} -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
