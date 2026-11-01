"""Score the AI chart views in docs/fresh/ai-views.md (follows the rules written there).

    python3 scripts/ft.py ai-score

Rules (from ai-views.md, written before the first view, not changed here):
  - every view predicts the direction 7 days later: yukarı / aşağı / yatay (yatay = within ±2%)
  - scoring compares the daily close 7 days later with the close the view was based on
  - baselines: coin flip (33%, three choices) and "always up"
  - the bot only considers using the views after 50+ scored predictions beat both

Scores go to docs/fresh/ai-scores.csv (one row per view, rewritten each run, so it is
idempotent). Totals: hit rate, the two baselines, and a one-sided binomial p-value
against chance (1/3). Runs in Docker (pandas reads the 1d candles).
"""

import csv
import math
import re
import sys
from datetime import date, timedelta
from pathlib import Path

HORIZON = 7
FLAT_BAND = 0.02
CHANCE = 1 / 3
ROW = re.compile(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*([A-Z0-9]+)\s*\|\s*([\d.]+)\s*\|.*?\|\s*(yukarı|aşağı|yatay)\s*\|\s*(\d)\s*\|")
FIELDS = ["date", "coin", "base_close", "call", "confidence", "due", "close_7d", "move", "actual", "hit"]


def parse_views(text: str) -> list[dict]:
    views = []
    for line in text.splitlines():
        m = ROW.match(line)
        if m:
            d, coin, close, call, conf = m.groups()
            views.append({"date": d, "coin": coin, "base_close": float(close), "call": call, "confidence": int(conf)})
    return views


def classify(move: float, band: float = FLAT_BAND) -> str:
    if move > band:
        return "yukarı"
    if move < -band:
        return "aşağı"
    return "yatay"


def score(views: list[dict], close_on, today: date) -> list[dict]:
    """close_on(coin, day) -> daily close of that UTC day, or None if not available yet."""
    rows = []
    for v in views:
        due = date.fromisoformat(v["date"]) + timedelta(days=HORIZON)
        row = {**v, "due": due.isoformat(), "close_7d": "", "move": "", "actual": "", "hit": ""}
        later = close_on(v["coin"], due) if due < today else None
        if later:
            move = later / v["base_close"] - 1
            actual = classify(move)
            row.update(close_7d=later, move=round(move, 5), actual=actual, hit=int(actual == v["call"]))
        rows.append(row)
    return rows


def binom_p_at_least(k: int, n: int, p: float = CHANCE) -> float:
    """One-sided P(X >= k) for X ~ Binomial(n, p)."""
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1))


def totals(rows: list[dict]) -> dict:
    done = [r for r in rows if r["hit"] != ""]
    n = len(done)
    hits = sum(int(r["hit"]) for r in done)
    always_up = sum(r["actual"] == "yukarı" for r in done)
    return {"n": n, "hits": hits, "hit_rate": hits / n if n else None, "always_up": always_up / n if n else None,
            "p_value": binom_p_at_least(hits, n) if n else None,
            "pending": len(rows) - n, "next_due": min((r["due"] for r in rows if r["hit"] == ""), default=None)}  # fmt: skip


def render(t: dict) -> str:
    if t["n"] == 0:
        first = (date.fromisoformat(t["next_due"]) + timedelta(days=1)).isoformat() if t["next_due"] else "-"
        return f"ai_score: henüz puanlanacak tahmin yok (ilk: {first}, {t['next_due']} kapanışıyla), bekleyen {t['pending']}"
    return (f"ai_score: {t['n']} tahmin puanlandı, isabet %{t['hit_rate'] * 100:.0f} | yazı-tura %33 | hep yukarı "
            f"%{t['always_up'] * 100:.0f} | şansa karşı p = {t['p_value']:.3f} | bekleyen {t['pending']}")  # fmt: skip


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in FIELDS})


def main() -> None:  # pragma: no cover - needs candles inside the container
    import pandas as pd

    fresh = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/freqtrade/fresh")
    data = Path("/freqtrade/user_data/data/binance")
    cache = {}

    def close_on(coin: str, day: date):
        if coin not in cache:
            p = data / f"{coin}_USDT-1d.feather"
            cache[coin] = pd.read_feather(p).set_index("date")["close"] if p.exists() else pd.Series(dtype=float)
        s = cache[coin]
        hit = s[s.index.normalize() == pd.Timestamp(day, tz="UTC")]
        return float(hit.iloc[0]) if len(hit) else None

    views = parse_views((fresh / "ai-views.md").read_text())
    rows = score(views, close_on, pd.Timestamp.now(tz="UTC").date())
    write_csv(fresh / "ai-scores.csv", rows)
    print(render(totals(rows)))


if __name__ == "__main__":
    main()
