"""Binance Demo Mode for the mini bot (Phase 5): fake money, but real orders on Binance's demo market.

    python3 scripts/ft.py minibot --demo --once        # NOT run yet: needs demo keys (Kaan's approval)

Safety rules, each one enforced in code below and tested in tests/test_minibot_demo.py:
  1. Keys come ONLY from the environment variables FTLAB_DEMO_KEY / FTLAB_DEMO_SECRET
     (they live in .env, never in a file in the repo). Missing -> refuse to start.
  2. The exchange is switched to demo with enable_demo_trading(True), then EVERY api url is
     checked: spot must be https://demo-api.binance.com, every other url a demo-*.binance.com
     host. One live url -> abort before any private call (balance, order).
  3. Spot only, LIMIT orders only (no market orders), sized by the same stake_for / VolTarget
     logic as the paper bot (bot.step decides, DemoBroker only sends what it decided).
  4. Its own state file (minibot/state.demo.json), so the paper account is never mixed in.

What is NOT done yet (before the first real demo run): reading back fills and partial fills
from the exchange. Until then the state records the orders that were SENT.
"""

import json
import os
from pathlib import Path
from urllib.parse import urlparse

KEY_ENV, SECRET_ENV = "FTLAB_DEMO_KEY", "FTLAB_DEMO_SECRET"
DEMO_SPOT_HOST = "demo-api.binance.com"
STATE_FILE = Path(__file__).resolve().parent / "state.demo.json"


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
    """Sends the paper bot's decisions as LIMIT orders to the demo exchange and records them."""

    def __init__(self, exchange, state: dict):
        assert_demo_urls(exchange)  # checked again right before the first private call
        self.exchange, self.state = exchange, state
        state.setdefault("orders", [])

    def _order(self, pair: str, side: str, amount: float, price: float) -> dict:
        if not pair.endswith("/USDT") or ":" in pair:  # "BTC/USDT:USDT" would be a futures market
            raise DemoRefused(f"refusing: {pair} is not a spot USDT pair")
        amount = float(self.exchange.amount_to_precision(pair, amount))
        price = float(self.exchange.price_to_precision(pair, price))
        order = self.exchange.create_order(pair, "limit", side, amount, price, {"timeInForce": "GTC"})
        self.state["orders"].append({"pair": pair, "side": side, "type": "limit", "amount": amount, "price": price,
                                     "id": order.get("id"), "status": order.get("status")})  # fmt: skip
        return order

    def buy(self, pair: str, amount: float, price: float) -> dict:
        return self._order(pair, "buy", amount, price)

    def sell(self, pair: str, amount: float, price: float) -> dict:
        return self._order(pair, "sell", amount, price)


def load_state(path: Path = STATE_FILE) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def save_state(state: dict, path: Path = STATE_FILE) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(path)
