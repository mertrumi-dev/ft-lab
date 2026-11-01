"""Tests for minibot/demo.py (Binance Demo Mode) with a fake exchange: no network, no keys."""

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from minibot import bot, demo, paper, signals  # noqa: E402

ENV = {demo.KEY_ENV: "fake-demo-key", demo.SECRET_ENV: "fake-demo-secret"}  # test values, not real keys
DEMO_API = {"public": "https://demo-api.binance.com/api/v3", "private": "https://demo-api.binance.com/api/v3",
            "fapiPublic": "https://demo-fapi.binance.com/fapi/v1"}  # fmt: skip
LIVE_API = {"public": "https://api.binance.com/api/v3", "private": "https://api.binance.com/api/v3"}
HOUR = 3_600_000


class FakeExchange:
    def __init__(self, config, demo_urls=DEMO_API):
        self.config, self.demo_urls = config, demo_urls
        self.urls = {"api": dict(LIVE_API)}
        self.options = config.get("options", {})
        self.orders, self.rows = [], []

    def enable_demo_trading(self, enable):
        if enable:
            self.urls["api"] = dict(self.demo_urls)

    def amount_to_precision(self, pair, amount):
        return f"{amount:.5f}"

    def price_to_precision(self, pair, price):
        return f"{price:.2f}"

    def create_order(self, symbol, type, side, amount, price, params):
        self.orders.append({"symbol": symbol, "type": type, "side": side, "amount": amount, "price": price, **params})
        return {"id": str(len(self.orders)), "status": "open"}

    def fetch_ohlcv(self, pair, timeframe, limit):
        return self.rows[-limit:]


def test_missing_keys_refuse_to_start():
    for env in ({}, {demo.KEY_ENV: "k"}, {demo.SECRET_ENV: "s"}, {demo.KEY_ENV: "", demo.SECRET_ENV: ""}):
        with pytest.raises(demo.DemoRefused, match="not set"):
            demo.demo_exchange(env, factory=FakeExchange)


def test_keys_come_from_env_and_urls_are_demo():
    ex = demo.demo_exchange(ENV, factory=FakeExchange)
    assert ex.config["apiKey"] == "fake-demo-key" and ex.config["secret"] == "fake-demo-secret"
    assert ex.urls["api"]["private"] == "https://demo-api.binance.com/api/v3"


@pytest.mark.parametrize("urls", [
    LIVE_API,  # enable_demo_trading did nothing
    {**DEMO_API, "fapiPublic": "https://fapi.binance.com/fapi/v1"},  # one live url left
    {**DEMO_API, "private": "https://demo-api.binance.com.evil.io/api/v3"},  # look-alike host
    {"public": "https://demo-api.binance.com/api/v3", "private": "https://testnet.binance.vision/api/v3"},
    {},
])  # fmt: skip
def test_any_live_or_wrong_url_aborts_before_private_calls(urls):
    with pytest.raises(demo.DemoRefused):
        demo.demo_exchange(ENV, factory=lambda cfg: FakeExchange(cfg, demo_urls=urls))


def test_non_spot_default_type_refused():
    def factory(cfg):
        return FakeExchange({**cfg, "options": {"defaultType": "future"}})

    with pytest.raises(demo.DemoRefused, match="spot"):
        demo.demo_exchange(ENV, factory=factory)


def test_broker_rechecks_urls_and_sends_limit_spot_orders_only():
    ex = demo.demo_exchange(ENV, factory=FakeExchange)
    state = {}
    broker = demo.DemoBroker(ex, state)
    broker.buy("BTC/USDT", 0.0012345, 65000.123)
    o = ex.orders[0]
    assert o == {"symbol": "BTC/USDT", "type": "limit", "side": "buy", "amount": 0.00123, "price": 65000.12, "timeInForce": "GTC"}
    assert state["orders"][0]["type"] == "limit" and state["orders"][0]["id"] == "1"
    with pytest.raises(demo.DemoRefused):
        broker.buy("BTC/USDT:USDT", 1, 1)  # futures symbol
    ex.urls["api"] = dict(LIVE_API)
    with pytest.raises(demo.DemoRefused):
        demo.DemoBroker(ex, {})  # urls changed after creation -> refused


def test_step_sends_the_same_voltarget_size_as_the_paper_decision():
    rng = np.random.default_rng(7)
    full = list(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, 4000))))
    close = next(full[i - 999 : i + 1] for i in range(999, len(full)) if signals.signal(full[i - 999 : i + 1]) == "buy")
    ex = demo.demo_exchange(ENV, factory=FakeExchange)
    ex.rows = [[i * HOUR, c, c, c, c, 1.0] for i, c in enumerate(close)]
    state = {"paper": paper.new_account(1000)}
    bot.step(state["paper"], ex, ex.rows[-1][0] + HOUR, pairs=["BTC/USDT"], broker=demo.DemoBroker(ex, state))
    pos = state["paper"]["positions"]["BTC/USDT"]
    assert pos["stake"] < 125.0  # VolTarget shrank it (wild synthetic coin)
    assert len(ex.orders) == 1 and ex.orders[0]["type"] == "limit" and ex.orders[0]["side"] == "buy"
    assert ex.orders[0]["amount"] == pytest.approx(pos["amount"], abs=1e-5)
    assert ex.orders[0]["price"] == pytest.approx(close[-1], abs=0.01)


def test_demo_state_is_separate_and_ignored_by_git():
    assert demo.STATE_FILE.name == "state.demo.json" and demo.STATE_FILE != bot.STATE_FILE
    assert "minibot/state.demo.json" in (ROOT / ".gitignore").read_text().splitlines()


def test_demo_keys_only_from_env_in_source():
    src = (ROOT / "minibot" / "demo.py").read_text()
    assert src.count('"apiKey"') == 1 and '"apiKey": key, "secret": secret' in src
    assert 'env.get(KEY_ENV, "")' in src and 'env.get(SECRET_ENV, "")' in src
    assert "open(" not in src.replace("json.loads(path.read_text())", "")  # never reads a key file


def test_ft_minibot_demo_passes_env_file_without_reading_it():
    import ft

    cmd = ft.build_commands(ft.parse_args(["minibot", "--demo", "--once"]))[0]
    assert cmd[cmd.index("--env-file") + 1].endswith(".env") and cmd[-1] == "--demo"
    plain = ft.build_commands(ft.parse_args(["minibot", "--once"]))[0]
    assert "--env-file" not in plain and "--demo" not in plain


def test_real_ccxt_binance_passes_the_guard_offline():
    pytest.importorskip("ccxt")
    ex = demo.demo_exchange(ENV)  # builds the object only; no request is sent
    assert all(".binance.com" in u and "//demo-" in u for u in ex.urls["api"].values())
    assert ex.options["defaultType"] == "spot"
