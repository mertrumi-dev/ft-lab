"""The mini bot's main loop.

    python3 scripts/ft.py minibot --once          # one pass over all pairs, then exit
    python3 scripts/ft.py minibot                 # run forever, one pass every hour

What one pass does, for each pair:
  1. Ask the exchange for the last 1000 one-hour candles (public data, no key).
  2. Throw away the newest candle: it is still forming, its close is not final.
  3. If we hold the coin and the last candle's low touched the stop -> sell at the stop.
  4. Otherwise compute the TrendEma signal and buy / sell / do nothing. With the default
     rule "voltarget" (same as the Freqtrade bot since 2026-11-01) a buy is sized by the
     coin's 30-day volatility; "trendema" keeps the old full-size stake.
  5. Save the account to minibot/state.json, so a restart continues where it stopped.
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from minibot import paper, signals

STATE_FILE = Path(__file__).resolve().parent / "state.json"
PAIRS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]
TIMEFRAME = "1h"
LIMIT = 1000  # 720 returns for the volatility + margin (also covers the 2 x EMA200 warm-up); Binance max per call
RULES = ("voltarget", "trendema")


def public_exchange():
    """Binance with NO credentials. Paper trading never needs a key."""
    import ccxt

    exchange = ccxt.binance({"enableRateLimit": True})
    assert not exchange.apiKey and not exchange.secret, "mini bot must never hold API keys"
    return exchange


def closed_candles(exchange, pair: str, now_ms: int) -> list[list[float]]:
    """[time, open, high, low, close, volume] rows whose hour has already ended."""
    rows = exchange.fetch_ohlcv(pair, TIMEFRAME, limit=LIMIT)
    hour_ms = 3_600_000
    return [r for r in rows if r[0] + hour_ms <= now_ms]


def step(acc: dict, exchange, now_ms: int, pairs: list[str] = PAIRS, rule: str = "voltarget") -> list[str]:
    """One pass over all pairs. Returns what happened, one line per action. (Demo mode: demo.step.)"""
    log, candles = [], {}
    for pair in pairs:
        candles[pair] = closed_candles(exchange, pair, now_ms)
    prices = {p: c[-1][4] for p, c in candles.items() if c}
    for pair, rows in candles.items():
        if not rows:
            continue
        stamp = datetime.fromtimestamp(rows[-1][0] / 1000, timezone.utc).isoformat()
        low, close = rows[-1][3], rows[-1][4]
        if paper.stop_hit(acc, pair, low):
            stop_price = acc["positions"][pair]["entry"] * (1 + paper.STOPLOSS)
            log.append(paper.sell(acc, pair, stop_price, stamp, "stoploss"))
            continue
        closes = [r[4] for r in rows]
        sig = signals.signal(closes)
        if sig == "buy":
            scale = signals.vol_scale(signals.realized_vol(closes)) if rule == "voltarget" else 1.0
            note = paper.buy(acc, pair, close, prices, stamp, scale)
        elif sig == "sell":
            note = paper.sell(acc, pair, close, stamp, "ema_cross_down")
        else:
            note = None
        if note:
            log.append(note)
    return log


def load_state(path: Path = STATE_FILE) -> dict:
    return json.loads(path.read_text()) if path.exists() else paper.new_account()


def save_state(acc: dict, path: Path = STATE_FILE) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(acc, indent=2))
    tmp.replace(path)  # write-then-rename: a crash never leaves half a file


def main() -> None:
    parser = argparse.ArgumentParser(description="ft-lab mini bot (paper trading only)")
    parser.add_argument("--once", action="store_true", help="one pass, then exit")
    parser.add_argument("--rule", choices=RULES, default="voltarget", help="sizing: voltarget (default) or trendema")
    parser.add_argument("--demo", action="store_true",
                        help="Binance Demo Mode: real orders with fake money (keys from FTLAB_DEMO_KEY/SECRET only)")
    args = parser.parse_args()

    if args.demo:
        from minibot import demo  # refuses to start without demo keys or with any non-demo url

        exchange = demo.demo_exchange()
        state_path, load, save = demo.STATE_FILE, demo.load_state, demo.save_state
    else:
        exchange = public_exchange()
        state_path, load, save = STATE_FILE, load_state, save_state
    while True:
        state = load(state_path)
        now_ms = int(time.time() * 1000)
        if args.demo:
            acc = state.setdefault("ledger", paper.new_account(demo.RESEARCH_EQUITY))
            lines = demo.step(acc, demo.DemoBroker(exchange, state), exchange, now_ms, rule=args.rule)
        else:
            acc = state
            lines = step(acc, exchange, now_ms, rule=args.rule)
        for line in lines:
            print(line, flush=True)
        save(state, state_path)
        prices = {p: pos["entry"] for p, pos in acc["positions"].items()}
        print(f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC  cash {acc['cash']:.2f}  "
              f"open {list(acc['positions'])}  closed trades {len(acc['closed'])}  "
              f"capital~{paper.capital(acc, prices):.2f}", flush=True)
        if args.once:
            return
        time.sleep(3600 - time.time() % 3600 + 30)  # 30 s after the next full hour


if __name__ == "__main__":
    main()
