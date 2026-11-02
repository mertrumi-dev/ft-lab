"""Download market-wide attention history for backtests: Wikipedia pageviews of the "Bitcoin" article.

    python3 scripts/attention.py            # writes user_data/data/external/wiki_bitcoin.json

One number per UTC day: how many people (agent=user, so no bots/spiders) read the English
Wikipedia "Bitcoin" article. A clean, keyless proxy for retail attention, daily since 2015-07-01.
It is market-wide on purpose: per-coin articles are messy (BNB has no article of its own, it
redirects to a section of "Binance"; XRP's article was renamed, so its history is split between
titles; the pageviews API does not follow redirects). docs/research/13-haber-sosyal-kaynaklar.md.

Source: Wikimedia Analytics REST API, per-article pageviews
  https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/Bitcoin/daily/START/END
No key. Wikimedia asks every client to send a descriptive User-Agent (done below) and to keep the
request rate low (one request per year of data here, a pause between them). Licence: Wikimedia
publishes pageview data as open data; check https://wikitech.wikimedia.org/wiki/Analytics before
redistributing (docs/research/13 lists it as "to be verified").

Like scripts/sentiment.py: stdlib only (runs on the Mac), output in user_data/data/ (gitignored).
Strategies use a day's value only from the NEXT UTC day on (trend_sentiment.fng_for_candles style),
so a number is never used before it existed.
"""

import json
import sys
import time
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "user_data" / "data" / "external" / "wiki_bitcoin.json"
ARTICLE = "Bitcoin"
FIRST_DAY = date(2015, 7, 1)  # the per-article API starts here
URL = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/{article}/daily/{start}/{end}"
USER_AGENT = "ft-lab-research/0.1 (crypto trading-rule research, one request per year of data; github mertrumi-dev)"
PAUSE_S = 5.0  # between requests; a 429 means slow down further, never retry fast
RETRIES = 3


def year_ranges(first: date, last: date) -> list[tuple[str, str]]:
    """[(YYYYMMDD, YYYYMMDD), ...] one per calendar year, clipped to [first, last]."""
    out = []
    for y in range(first.year, last.year + 1):
        a, b = max(first, date(y, 1, 1)), min(last, date(y, 12, 31))
        out.append((a.strftime("%Y%m%d"), b.strftime("%Y%m%d")))
    return out


def parse(payload: dict) -> dict[str, int]:
    """API items -> {"YYYY-MM-DD": views}."""
    out = {}
    for item in payload.get("items", []):
        ts = item["timestamp"]  # "2015070100"
        out[f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}"] = int(item["views"])
    return out


def wait_after_429(retry_after: str | None, attempt: int) -> float:
    """Seconds to wait after HTTP 429: the server's Retry-After if given, else 60, 120, 240 s."""
    try:
        return max(float(retry_after), 1.0)
    except (TypeError, ValueError):
        return 60.0 * 2**attempt


def fetch(start: str, end: str, article: str = ARTICLE) -> dict[str, int]:  # pragma: no cover - network
    import urllib.error

    req = urllib.request.Request(URL.format(article=article, start=start, end=end), headers={"User-Agent": USER_AGENT})
    for attempt in range(RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return parse(json.load(r))
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == RETRIES:
                raise
            wait = wait_after_429(e.headers.get("Retry-After"), attempt)
            print(f"429 Too Many Requests: waiting {wait:.0f} s", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError("unreachable")


def main() -> int:  # pragma: no cover - network
    today = datetime.now(timezone.utc).date()
    days: dict[str, int] = {}
    for i, (a, b) in enumerate(year_ranges(FIRST_DAY, today)):
        if i:
            time.sleep(PAUSE_S)
        days.update(fetch(a, b))
    if not days:
        print("no data received", file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dict(sorted(days.items()))))
    first, last = min(days), max(days)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(days)} days, {first} -> {last}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
