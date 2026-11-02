"""Binance Demo Mode for the mini bot (Phase 5): fake money, but real orders on Binance's demo market.

    python3 scripts/ft.py minibot --demo --once        # NOT run yet: needs demo keys (Kaan's approval)

Safety rules, each one enforced in code below and tested in tests/test_minibot_demo.py:
  1. Keys come ONLY from the environment variables FTLAB_DEMO_KEY / FTLAB_DEMO_SECRET
     (they live in .env, never in a file in the repo). Missing -> refuse to start.
  2. The exchange is switched to demo with enable_demo_trading(True), then EVERY api url is
     checked: spot must be https://demo-api.binance.com, every other url a demo-*.binance.com
     host. One live url -> abort before any private call (balance, order).
  3. Spot only, LIMIT orders only (no market orders), sized by the same stake_for / VolTarget
     logic as the paper bot.
  4. Its own state file (minibot/state.demo.json), so the paper account is never mixed in.
  5. Every order is followed until it is filled or cancelled; after 10 minutes (the same
     unfilled timeout as the Freqtrade config) it is cancelled. Only what REALLY filled is
     booked in the ledger (partial fills included), with the real average price and fee.
  6. Risk is measured on our own ledger, which starts at RESEARCH_EQUITY (1000 USDT) and only
     changes through real fills; a stake is also capped by the demo account's free USDT. So a
     big demo balance can never make positions bigger, and the kill switch sees demo results.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from minibot import bot, paper, signals

KEY_ENV, SECRET_ENV = "FTLAB_DEMO_KEY", "FTLAB_DEMO_SECRET"
DEMO_SPOT_HOST = "demo-api.binance.com"
STATE_FILE = Path(__file__).resolve().parent / "state.demo.json"
RESEARCH_EQUITY = 1000.0  # the ledger's start; risk is never measured on the (bigger) demo balance
UNFILLED_TIMEOUT_S = 10 * 60  # same as config.json unfilledtimeout (10 minutes)
POLL_S = 10
# The stop lives ON the exchange: right after an entry fill a Binance spot STOP_LOSS_LIMIT
# order is placed (stopPrice = entry x 0.92, limit 1% below it), so it triggers within the
# hour like the backtest instead of up to 1h late. ccxt builds it from
# create_order(pair, "limit", "sell", amount, limit, {"stopLossPrice": stopPrice}).
# Fallback, if the stop order cannot be placed: the hourly check sends a limit 1% below the
# last close (a limit AT the stop price may never fill in a fall: the replay saw an ETH stop
# fill 2 days late).
STOP_LIMIT_BELOW = 0.01
DONE = ("closed", "canceled", "cancelled", "expired", "rejected")


class DemoRefused(SystemExit):
    """Raised (and exits the program) whenever a safety rule is not met."""


def keys_from_env(env=os.environ) -> tuple[str, str]:
    key, secret = env.get(KEY_ENV, ""), env.get(SECRET_ENV, "")
    if not key or not secret:
        raise DemoRefused(f"refusing to start: {KEY_ENV} / {SECRET_ENV} not set (they belong in .env, demo account only)")
    return key, secret


def assert_demo_urls(exchange) -> None:
    """Every api url must be a Binance demo host; spot must be demo-api.binance.com."""
    api = exchange.urls.get("api", {})
    urls = api.values() if isinstance(api, dict) else [api]
    hosts = {u: urlparse(u).hostname or "" for u in urls}
    live = [u for u, h in hosts.items() if not (h.startswith("demo-") and h.endswith(".binance.com"))]
    if not hosts or live:
        raise DemoRefused(f"refusing: not a Binance demo url: {live or 'no urls'}")
    for name in ("public", "private"):
        if urlparse(api.get(name, "")).hostname != DEMO_SPOT_HOST:
            raise DemoRefused(f"refusing: spot {name} url is not {DEMO_SPOT_HOST}: {api.get(name)!r}")


def demo_exchange(env=os.environ, factory=None):
    """A ccxt Binance object in demo mode, checked before it is returned. Nothing private is called here."""
    key, secret = keys_from_env(env)
    if factory is None:
        import ccxt

        factory = ccxt.binance
    # The only place in minibot/ that passes keys to ccxt; values come only from keys_from_env (rule 1).
    exchange = factory({"enableRateLimit": True, "options": {"defaultType": "spot"}, "apiKey": key, "secret": secret})
    exchange.enable_demo_trading(True)
    assert_demo_urls(exchange)
    if exchange.options.get("defaultType", "spot") != "spot":
        raise DemoRefused("refusing: defaultType is not spot")
    return exchange


class DemoBroker:
    """Sends LIMIT orders to the demo exchange, waits for the result and records every order."""

    def __init__(self, exchange, state: dict, sleep=time.sleep, clock=time.monotonic):
        assert_demo_urls(exchange)  # checked again right before the first private call
        # ccxt rounds amounts/prices with the market list; without it amount_to_precision raises
        # "markets not loaded" on the first order (the keyless data exchange is a different object).
        exchange.load_markets()  # public call on the demo host checked just above
        self.exchange, self.state, self.sleep, self.clock = exchange, state, sleep, clock
        self.at = None  # the hour demo.step is trading (set by demo.step), recorded with each order
        state.setdefault("orders", [])

    def free_usdt(self) -> float:
        return float(self.exchange.fetch_balance().get("free", {}).get("USDT", 0.0) or 0.0)

    def _wait(self, order: dict, pair: str) -> dict:
        """Poll until filled/cancelled; after UNFILLED_TIMEOUT_S cancel and read the final state."""
        start = self.clock()
        while order.get("status") not in DONE:
            if self.clock() - start >= UNFILLED_TIMEOUT_S:
                self.exchange.cancel_order(order["id"], pair)
                order = self.exchange.fetch_order(order["id"], pair)
                order["timed_out"] = True
                break
            self.sleep(POLL_S)
            order = self.exchange.fetch_order(order["id"], pair)
        return order

    def _order(self, pair: str, side: str, kind: str, amount: float, price: float) -> dict:
        """Returns {"filled": coins we really got/sold, "price": average, "fee_usdt": fee in USDT}."""
        if not pair.endswith("/USDT") or ":" in pair:  # "BTC/USDT:USDT" would be a futures market
            raise DemoRefused(f"refusing: {pair} is not a spot USDT pair")
        amount = float(self.exchange.amount_to_precision(pair, amount))
        price = float(self.exchange.price_to_precision(pair, price))
        created = self.at or datetime.now(timezone.utc).isoformat()
        order = self.exchange.create_order(pair, "limit", side, amount, price, {"timeInForce": "GTC"})
        order = self._wait(order, pair)
        fill = fill_result(order, pair, side)
        self.state["orders"].append({
            "pair": pair, "side": side, "kind": kind, "type": "limit", "requested": price, "amount": amount,
            "id": order.get("id"), "status": order.get("status"), "timed_out": order.get("timed_out", False),
            "filled": fill["filled"], "average": fill["price"], "fee_usdt": fill["fee_usdt"],
            "candle": created, "created": created,
            "filled_at": datetime.now(timezone.utc).isoformat() if fill["filled"] else None,
        })  # fmt: skip
        return fill

    def buy(self, pair: str, amount: float, price: float) -> dict:
        return self._order(pair, "buy", "entry", amount, price)

    # --- stop-loss order on the exchange -----------------------------------------------------

    def place_stop(self, pair: str, amount: float, stop_price: float) -> str | None:
        """STOP_LOSS_LIMIT sell: triggers at stop_price, then sells with a limit 1% below. None if refused."""
        amount = float(self.exchange.amount_to_precision(pair, amount))
        stop = float(self.exchange.price_to_precision(pair, stop_price))
        limit = float(self.exchange.price_to_precision(pair, stop_price * (1 - STOP_LIMIT_BELOW)))
        try:
            order = self.exchange.create_order(pair, "limit", "sell", amount, limit, {"stopLossPrice": stop, "timeInForce": "GTC"})
        except Exception as e:  # e.g. the order type not allowed: fall back to the hourly stop check
            self.state.setdefault("errors", []).append(f"{self.at} stop order refused for {pair}: {e}")
            return None
        self.state["orders"].append({
            "pair": pair, "side": "sell", "kind": "stoploss", "type": "stop_loss_limit", "requested": stop,
            "limit": limit, "amount": amount, "id": order.get("id"), "status": order.get("status"), "timed_out": False,
            "filled": 0.0, "average": None, "fee_usdt": 0.0, "candle": None, "created": self.at, "filled_at": None,
        })  # fmt: skip
        return order.get("id")

    def _stop_result(self, order: dict, pair: str) -> dict:
        fill = fill_result(order, pair, "sell")
        ts = order.get("lastTradeTimestamp")
        when = datetime.fromtimestamp(ts / 1000, timezone.utc).isoformat() if ts else self.at
        for rec in self.state["orders"]:
            if rec.get("id") == order.get("id") and rec.get("type") == "stop_loss_limit":
                rec.update(status=order.get("status"), filled=fill["filled"], average=fill["price"] if fill["filled"] else None,
                           fee_usdt=fill["fee_usdt"], candle=when if fill["filled"] else None,
                           filled_at=when if fill["filled"] else None)  # fmt: skip
        return {**fill, "done": order.get("status") in DONE, "ts": ts}

    def check_stop(self, pair: str, order_id: str) -> dict:
        return self._stop_result(self.exchange.fetch_order(order_id, pair), pair)

    def cancel_stop(self, pair: str, order_id: str) -> dict:
        """Cancel before a signal exit; whatever filled before the cancel is returned (and booked by the caller)."""
        try:
            self.exchange.cancel_order(order_id, pair)
        except Exception as e:  # already filled/cancelled: the fetch below tells what happened
            self.state.setdefault("errors", []).append(f"{self.at} cancel stop {pair}: {e}")
        return self._stop_result(self.exchange.fetch_order(order_id, pair), pair)

    def sell(self, pair: str, amount: float, price: float, kind: str = "exit") -> dict:
        return self._order(pair, "sell", kind, amount, price)


def fill_result(order: dict, pair: str, side: str) -> dict:
    """What really happened: filled amount (net of a fee paid in the coin), average price, fee in USDT.

    Binance takes the fee in the coin you receive (or in BNB). A fee in the coin we bought means we
    hold less coin; a fee in USDT is a cost; a fee in another coin (BNB) is recorded but not converted.
    """
    filled = float(order.get("filled") or 0.0)
    price = float(order.get("average") or order.get("price") or 0.0)
    base = pair.split("/")[0]
    fee_usdt = 0.0
    for fee in order.get("fees") or ([order["fee"]] if order.get("fee") else []):
        cost, cur = float(fee.get("cost") or 0.0), fee.get("currency")
        if cur == "USDT":
            fee_usdt += cost
        elif cur == base and side == "buy":
            filled -= cost  # we received less coin
            fee_usdt += cost * price
    return {"filled": max(filled, 0.0), "price": price, "fee_usdt": fee_usdt}


def step(acc: dict, broker: DemoBroker, exchange, now_ms: int, pairs: list[str] = bot.PAIRS, rule: str = "voltarget") -> list[str]:
    """Like bot.step, but every decision becomes a real demo order and the ledger books only real fills."""
    broker.at = datetime.fromtimestamp(now_ms / 1000, timezone.utc).isoformat()
    log, candles = [], {p: bot.closed_candles(exchange, p, now_ms) for p in pairs}
    prices = {p: c[-1][4] for p, c in candles.items() if c}
    # Exits first, then entries (like Freqtrade): a slot freed this hour can be used this hour.
    entries = []
    for pair, rows in candles.items():
        if not rows:
            continue
        stamp = datetime.fromtimestamp(rows[-1][0] / 1000, timezone.utc).isoformat()
        low, close = rows[-1][3], rows[-1][4]
        pos = acc["positions"].get(pair)
        closes = [r[4] for r in rows]
        sig = signals.signal(closes)
        stop_id = pos.get("stop_order") if pos else None
        if stop_id:  # the stop order on the exchange: did it fill?
            f = broker.check_stop(pair, stop_id)
            if f["filled"] > 0:
                log.append(_book_stop(acc, pair, f, stamp, now_ms))
                if pair not in acc["positions"]:
                    continue
                pos = acc["positions"][pair]
            elif f["done"]:  # cancelled/expired by the exchange: fall back to the hourly check
                pos["stop_order"] = stop_id = None
        if pos is not None and not stop_id and paper.stop_hit(acc, pair, low):  # fallback only
            f = broker.sell(pair, pos["amount"], close * (1 - STOP_LIMIT_BELOW), kind="stoploss")
            note = paper.close_from_fill(acc, pair, f["filled"], f["price"], f["fee_usdt"], stamp, "stoploss")
            if note and pair not in acc["positions"]:
                paper.after_close(acc, pair, now_ms, "stoploss")
            log.append(note or f"STOP {pair}: sell order not filled")
        elif sig == "sell" and pos is not None:
            if stop_id:  # cancel the exchange stop first, book anything it already sold
                f = broker.cancel_stop(pair, stop_id)
                pos["stop_order"] = None
                if f["filled"] > 0:
                    log.append(_book_stop(acc, pair, f, stamp, now_ms))
                    if pair not in acc["positions"]:
                        continue
                    pos = acc["positions"][pair]
            f = broker.sell(pair, pos["amount"], close)
            note = paper.close_from_fill(acc, pair, f["filled"], f["price"], f["fee_usdt"], stamp, "ema_cross_down")
            if note and pair not in acc["positions"]:
                paper.after_close(acc, pair, now_ms, "ema_cross_down")
            log.append(note or f"SELL {pair}: not filled within {UNFILLED_TIMEOUT_S // 60} min, cancelled")
        elif sig == "buy" and pos is None:
            entries.append((pair, closes, stamp))
    for pair, closes, stamp in entries:
        close = closes[-1]
        if paper.entry_blocked(acc, pair, now_ms):
            continue
        if paper.kill_switch_hit(acc):
            log.append(f"KILL SWITCH: no new trades ({pair} refused)")
            continue
        scale = signals.vol_scale(signals.realized_vol(closes)) if rule == "voltarget" else 1.0
        stake = min(paper.stake_for(acc, prices, scale), broker.free_usdt())  # ledger risk, real cash cap
        if stake < 10:
            continue
        f = broker.buy(pair, stake / close, close)
        note = paper.open_from_fill(acc, pair, f["filled"], f["price"], f["fee_usdt"], stamp)
        if note:
            stop_price = f["price"] * (1 + paper.STOPLOSS)
            acc["positions"][pair]["stop_order"] = broker.place_stop(pair, f["filled"], stop_price)
        log.append(note or f"BUY {pair}: not filled within {UNFILLED_TIMEOUT_S // 60} min, cancelled")
    return log


def _book_stop(acc: dict, pair: str, f: dict, stamp: str, now_ms: int) -> str:
    """Book an exchange stop fill; cooldown and stop guard start at the real fill time."""
    note = paper.close_from_fill(acc, pair, f["filled"], f["price"], f["fee_usdt"], stamp, "stoploss")
    if pair not in acc["positions"]:
        paper.after_close(acc, pair, int(f["ts"]) if f.get("ts") else now_ms, "stoploss")
    return f"{note} (stop order on the exchange)"


def load_state(path: Path = STATE_FILE) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def save_state(state: dict, path: Path = STATE_FILE) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(path)
