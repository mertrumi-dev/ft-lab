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
        self.plans, self.canceled, self._script = [], [], {}
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

    # scripted fills: each create_order pops the next plan, default = filled at once
    plans: list = []
    usdt_free = 100_000.0
    canceled: list = []

    def create_order(self, symbol, type, side, amount, price, params):
        self.orders.append({"symbol": symbol, "type": type, "side": side, "amount": amount, "price": price, **params})
        oid = str(len(self.orders))
        plan = self.plans.pop(0) if self.plans else [{"status": "closed", "filled": amount, "average": price}]
        self._script = {oid: list(plan)}
        self._last = {"id": oid, "status": "open", "filled": 0.0, "amount": amount, "price": price}
        if plan and plan[0].get("status") == "closed" and len(plan) == 1:  # instant fill
            return {**self._last, **plan[0]}
        return dict(self._last)

    def fetch_order(self, oid, symbol):
        script = self._script.get(oid, [])
        if script:
            self._last = {**self._last, **script.pop(0)}
        return dict(self._last)

    def cancel_order(self, oid, symbol):
        self.canceled.append(oid)
        self._script[oid] = []  # like the real exchange: after a cancel the order stays cancelled
        self._last = {**self._last, "status": "canceled"}

    def fetch_balance(self):
        return {"free": {"USDT": self.usdt_free}}

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
    fill = broker.buy("BTC/USDT", 0.0012345, 65000.123)
    assert fill == {"filled": 0.00123, "price": 65000.12, "fee_usdt": 0.0}
    o = ex.orders[0]
    assert o == {"symbol": "BTC/USDT", "type": "limit", "side": "buy", "amount": 0.00123, "price": 65000.12, "timeInForce": "GTC"}
    assert state["orders"][0]["type"] == "limit" and state["orders"][0]["id"] == "1" and state["orders"][0]["kind"] == "entry"
    with pytest.raises(demo.DemoRefused):
        broker.buy("BTC/USDT:USDT", 1, 1)  # futures symbol
    ex.urls["api"] = dict(LIVE_API)
    with pytest.raises(demo.DemoRefused):
        demo.DemoBroker(ex, {})  # urls changed after creation -> refused


def buy_window():
    rng = np.random.default_rng(7)
    full = list(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, 4000))))
    return next(full[i - 999 : i + 1] for i in range(999, len(full)) if signals.signal(full[i - 999 : i + 1]) == "buy")


def demo_setup(plans=(), usdt_free=100_000.0):
    close = buy_window()
    ex = demo.demo_exchange(ENV, factory=FakeExchange)
    ex.rows = [[i * HOUR, c, c, c, c, 1.0] for i, c in enumerate(close)]
    ex.plans, ex.usdt_free = list(plans), usdt_free
    state = {"ledger": paper.new_account(demo.RESEARCH_EQUITY)}
    clock = iter(range(0, 10_000, demo.POLL_S))
    broker = demo.DemoBroker(ex, state, sleep=lambda s: None, clock=lambda: next(clock))
    return close, ex, state, broker


def run(close, ex, state, broker):
    return demo.step(state["ledger"], broker, ex, ex.rows[-1][0] + HOUR, pairs=["BTC/USDT"])


def test_step_sends_the_voltarget_size_and_books_the_fill():
    close, ex, state, broker = demo_setup()
    log = run(close, ex, state, broker)
    expected_stake = 125.0 * signals.vol_scale(signals.realized_vol(close))
    assert expected_stake < 125.0  # VolTarget shrank it (wild synthetic coin)
    o = ex.orders[0]
    assert o["type"] == "limit" and o["side"] == "buy" and o["amount"] == pytest.approx(expected_stake / close[-1], abs=1e-5)
    pos = state["ledger"]["positions"]["BTC/USDT"]
    assert pos["amount"] == pytest.approx(o["amount"]) and pos["entry"] == pytest.approx(close[-1], abs=0.01)
    assert log[0].startswith("BUY BTC/USDT") and state["orders"][0]["filled"] == pytest.approx(o["amount"])


def test_partial_fill_then_timeout_cancel_books_only_what_filled():
    plan = [{"status": "open", "filled": 0.0}, {"status": "open", "filled": 0.4}]  # stays open -> timeout
    close, ex, state, broker = demo_setup(plans=[[{"status": "open"}] + plan + [{"status": "open", "filled": 0.4}] * 100])
    ex.amount_to_precision = lambda pair, a: "1.00000"  # order 1 coin, 0.4 fills
    ex.price_to_precision = lambda pair, p: "10.00"
    run(close, ex, state, broker)
    assert ex.canceled == ["1"]  # cancelled after the 10-minute timeout
    rec = state["orders"][0]
    assert rec["timed_out"] and rec["status"] == "canceled" and rec["filled"] == pytest.approx(0.4)
    pos = state["ledger"]["positions"]["BTC/USDT"]
    assert pos["amount"] == pytest.approx(0.4) and pos["stake"] == pytest.approx(4.0)
    assert state["ledger"]["cash"] == pytest.approx(demo.RESEARCH_EQUITY - 4.0)


def test_unfilled_order_is_cancelled_and_nothing_is_booked():
    close, ex, state, broker = demo_setup(plans=[[{"status": "open"}] * 200])
    log = run(close, ex, state, broker)
    assert ex.canceled == ["1"] and not state["ledger"]["positions"]
    assert state["ledger"]["cash"] == demo.RESEARCH_EQUITY and "not filled within 10 min" in log[0]


def test_fee_in_the_bought_coin_reduces_the_position():
    close, ex, state, broker = demo_setup()
    ex.amount_to_precision = lambda pair, a: "1.00000"
    ex.price_to_precision = lambda pair, p: "10.00"
    ex.plans = [[{"status": "closed", "filled": 1.0, "average": 10.0, "fee": {"cost": 0.001, "currency": "BTC"}}]]
    run(close, ex, state, broker)
    pos = state["ledger"]["positions"]["BTC/USDT"]
    assert pos["amount"] == pytest.approx(0.999) and pos["stake"] == pytest.approx(0.999 * 10 + 0.01)


def test_big_demo_balance_cannot_enlarge_risk_and_small_one_caps_the_stake():
    close, ex, state, broker = demo_setup(usdt_free=1_000_000.0)
    run(close, ex, state, broker)
    big = ex.orders[0]["amount"] * close[-1]
    assert big <= 125.0 + 0.01  # never more than the 1000-USDT ledger allows
    close, ex, state, broker = demo_setup(usdt_free=40.0)
    run(close, ex, state, broker)
    assert ex.orders[0]["amount"] * close[-1] <= 40.0 + 0.01  # capped by the real free USDT


def test_partial_sell_keeps_the_rest_open_and_kill_switch_uses_the_ledger():
    acc = paper.new_account(1000)
    paper.open_from_fill(acc, "BTC/USDT", 2.0, 50.0, 0.0, "t0")
    paper.close_from_fill(acc, "BTC/USDT", 0.5, 40.0, 0.0, "t1", "test")
    pos = acc["positions"]["BTC/USDT"]
    assert pos["amount"] == pytest.approx(1.5) and pos["stake"] == pytest.approx(75.0)
    assert acc["realized"] == pytest.approx(1000 - 5.0)
    acc["realized"] = 790.0
    _, ex, state, broker = demo_setup()
    state["ledger"] = {**paper.new_account(1000), "realized": 790.0}
    log = demo.step(state["ledger"], broker, ex, ex.rows[-1][0] + HOUR, pairs=["BTC/USDT"])
    assert "KILL SWITCH" in log[0] and not ex.orders


def test_execution_report_reads_demo_fills(tmp_path):
    import json

    import execution

    _, ex, state, broker = demo_setup()
    run(_, ex, state, broker)
    path = tmp_path / "state.demo.json"
    path.write_text(json.dumps(state))
    orders, fees = execution.read_demo_state(path)
    assert len(orders) == 1 and orders[0].kind == "entry" and orders[0].fill and orders[0].filled > 0
    s = execution.summarize(orders, fees, lambda pair, when: None)
    assert s["orders"] == 1 and s["filled"] == 1 and s["fill_rate_entries"] == 1.0


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
