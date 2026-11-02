"""Tests for minibot/demo.py (Binance Demo Mode) with a fake exchange: no network, no keys."""

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from minibot import bot, demo, paper, signals  # noqa: E402
import replay  # noqa: E402

ENV = {demo.KEY_ENV: "fake-demo-key", demo.SECRET_ENV: "fake-demo-secret"}  # test values, not real keys
DEMO_API = {"public": "https://demo-api.binance.com/api/v3", "private": "https://demo-api.binance.com/api/v3",
            "fapiPublic": "https://demo-fapi.binance.com/fapi/v1"}  # fmt: skip
LIVE_API = {"public": "https://api.binance.com/api/v3", "private": "https://api.binance.com/api/v3"}
HOUR = H = 3_600_000


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

    markets = None  # like ccxt: precision helpers need load_markets() first

    def load_markets(self):  # Binance demo spot limits, measured 2026-11-02
        lim = {"limits": {"amount": {"min": 0.00001}, "cost": {"min": 5.0}}}
        self.markets = {p: lim for p in ("BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT")}
        return self.markets

    def amount_to_precision(self, pair, amount):
        if self.markets is None:
            raise RuntimeError("binance markets not loaded")
        return f"{amount:.5f}"

    def price_to_precision(self, pair, price):
        if self.markets is None:
            raise RuntimeError("binance markets not loaded")
        return f"{price:.2f}"

    # scripted fills: each create_order pops the next plan, default = filled at once
    plans: list = []
    usdt_free = 100_000.0
    canceled: list = []

    def create_order(self, symbol, type, side, amount, price, params):
        if "stopLossPrice" in params:  # like Binance: a stop order waits untriggered
            self.stop_orders = getattr(self, "stop_orders", 0) + 1
            return {"id": f"stop{self.stop_orders}", "status": "open", "filled": 0.0}
        self.orders.append({"symbol": symbol, "type": type, "side": side, "amount": amount, "price": price, **params})
        oid = str(len(self.orders))
        plan = self.plans.pop(0) if self.plans else [{"status": "closed", "filled": amount, "average": price}]
        self._script = {oid: list(plan)}
        self._last = {"id": oid, "status": "open", "filled": 0.0, "amount": amount, "price": price}
        if plan and plan[0].get("status") == "closed" and len(plan) == 1:  # instant fill
            self._remember_fee(oid, plan[0])
            return {**self._last, **plan[0]}  # like Binance's FULL response: the fills (fee) are included
        return dict(self._last)

    _fees: dict = {}
    raise_next: list = []  # exceptions fetch_order raises first (network trouble)
    coin_free: dict = {}  # free coin balances; missing = not reported

    def _remember_fee(self, oid, step):
        fees = [step["fee"]] if step.get("fee") else list(step.get("fees") or [])
        if fees:
            self._fees = {**self._fees, oid: fees}

    def fetch_order_trades(self, oid, symbol):
        return [{"fee": f} for f in self._fees.get(oid, [])]

    def fetch_order(self, oid, symbol):
        if str(oid).startswith("stop"):  # untriggered stop order
            return {"id": oid, "status": "open", "filled": 0.0}
        if self.raise_next:
            raise self.raise_next.pop(0)
        script = self._script.get(oid, [])
        if script:
            step = script.pop(0)
            self._remember_fee(oid, step)
            self._last = {**self._last, **step}
        # like Binance GET /api/v3/order: the order status carries no fee (ccxt: fee None, fees [])
        return {k: v for k, v in self._last.items() if k not in ("fee", "fees")}

    def cancel_order(self, oid, symbol):
        self.canceled.append(oid)
        self._script[oid] = []  # like the real exchange: after a cancel the order stays cancelled
        self._last = {**self._last, "status": "canceled"}

    def fetch_balance(self):
        return {"free": {"USDT": self.usdt_free, **self.coin_free}}

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
    expected_stake = 123.75 * signals.vol_scale(signals.realized_vol(close))  # 1000 x 0.99 x 1% / 8%
    assert expected_stake < 123.75  # VolTarget shrank it (wild synthetic coin)
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
    assert big <= 123.75 + 0.01  # never more than the 1000-USDT ledger allows
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
    entry, stop = orders  # the entry fill + the stop order waiting on the exchange
    assert entry.kind == "entry" and entry.fill and entry.filled > 0
    assert stop.kind == "stoploss" and stop.fill is None and stop.status == "open"
    s = execution.summarize(orders, fees, lambda pair, when: None)
    assert s["orders"] == 2 and s["filled"] == 1 and s["fill_rate_entries"] == 1.0


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



# --- stop-loss order on the exchange ------------------------------------------------------------


class StopFake(FakeExchange):
    """Records every call in order; stop orders stay open until a test fills them."""

    def __init__(self, config, demo_urls=DEMO_API):
        super().__init__(config, demo_urls)
        self.calls, self.stops, self.refuse_stop = [], {}, False

    def create_order(self, symbol, type, side, amount, price, params):
        if "stopLossPrice" in params:
            if self.refuse_stop:
                raise RuntimeError("binance triggerPrice parameter is not allowed")
            oid = f"S{len(self.stops) + 1}"
            self.stops[oid] = {"id": oid, "status": "open", "filled": 0.0, "amount": amount, "price": price,
                               "stop": params["stopLossPrice"]}  # fmt: skip
            self.calls.append(("stop", symbol, amount, price, params["stopLossPrice"]))
            return dict(self.stops[oid])
        self.calls.append((side, symbol, amount, price))
        return super().create_order(symbol, type, side, amount, price, params)

    def fetch_order(self, oid, symbol):
        return dict(self.stops[oid]) if oid in self.stops else super().fetch_order(oid, symbol)

    def cancel_order(self, oid, symbol):
        self.calls.append(("cancel", oid))
        if oid in self.stops:
            if self.stops[oid]["status"] == "open":
                self.stops[oid]["status"] = "canceled"
            return
        super().cancel_order(oid, symbol)


def stop_setup():
    close = buy_window()
    ex = demo.demo_exchange(ENV, factory=StopFake)
    ex.rows = [[i * HOUR, c, c, c, c, 1.0] for i, c in enumerate(close)]
    ex.amount_to_precision = lambda pair, a: f"{a:.5f}"
    ex.price_to_precision = lambda pair, p: f"{p:.4f}"
    state = {"ledger": paper.new_account(demo.RESEARCH_EQUITY)}
    broker = demo.DemoBroker(ex, state, sleep=lambda s: None, clock=iter(range(0, 10**6, demo.POLL_S)).__next__)
    return close, ex, state, broker


def test_entry_fill_places_a_stop_loss_limit_on_the_exchange():
    close, ex, state, broker = stop_setup()
    demo.step(state["ledger"], broker, ex, ex.rows[-1][0] + HOUR, pairs=["BTC/USDT"])
    kind, pair, amount, limit, stop = ex.calls[1]
    pos = state["ledger"]["positions"]["BTC/USDT"]
    assert ex.calls[0][0] == "buy" and kind == "stop" and pair == "BTC/USDT"
    assert amount == pytest.approx(pos["amount"], abs=1e-5)
    assert stop == pytest.approx(pos["entry"] * 0.92, abs=1e-4) and limit == pytest.approx(stop * 0.99, abs=1e-3)
    assert pos["stop_order"] == "S1"
    rec = state["orders"][-1]
    assert rec["type"] == "stop_loss_limit" and rec["kind"] == "stoploss" and rec["status"] == "open"


def test_triggered_stop_is_booked_with_its_real_fill_time():
    close, ex, state, broker = stop_setup()
    now = ex.rows[-1][0] + HOUR
    demo.step(state["ledger"], broker, ex, now, pairs=["BTC/USDT"])
    pos = state["ledger"]["positions"]["BTC/USDT"]
    fill_ts = now + 3 * HOUR
    ex.stops["S1"].update(status="closed", filled=pos["amount"], average=pos["entry"] * 0.92, lastTradeTimestamp=fill_ts)
    ex.rows.append([now, close[-1], close[-1], close[-1], close[-1], 1.0])  # one more closed candle, no signal
    log = demo.step(state["ledger"], broker, ex, now + 5 * HOUR, pairs=["BTC/USDT"])
    acc = state["ledger"]
    assert "BTC/USDT" not in acc["positions"] and acc["closed"][-1]["reason"] == "stoploss"
    assert "stop order on the exchange" in log[0]
    assert acc["cooldown"]["BTC/USDT"] == fill_ts + 2 * HOUR and acc["stop_times"] == [fill_ts]
    assert acc["realized"] == pytest.approx(1000 - pos["stake"] * 0.08, rel=0.01)


def test_signal_exit_cancels_the_stop_first_then_sells():
    close, ex, state, broker = stop_setup()
    now = ex.rows[-1][0] + HOUR
    demo.step(state["ledger"], broker, ex, now, pairs=["BTC/USDT"])
    # a falling path: EMA20 crosses below EMA50 -> sell signal (price stays above the stop)
    start = close[-1]
    path = [start * (1 - 0.0005 * k) for k in range(1, 200)]
    for k, p in enumerate(path):
        ex.rows.append([now + k * HOUR, p, p, p, p, 1.0])
        if signals.signal([r[4] for r in ex.rows]) == "sell":
            break
    assert signals.signal([r[4] for r in ex.rows]) == "sell" and min(path[: k + 1]) > start * 0.92
    demo.step(state["ledger"], broker, ex, ex.rows[-1][0] + HOUR, pairs=["BTC/USDT"])
    tail = ex.calls[2:]
    assert tail[0] == ("cancel", "S1") and tail[1][0] == "sell"  # cancel BEFORE the exit order
    assert ex.stops["S1"]["status"] == "canceled" and "BTC/USDT" not in state["ledger"]["positions"]
    assert state["ledger"]["closed"][-1]["reason"] == "ema_cross_down"


def test_refused_stop_order_falls_back_to_the_hourly_check():
    close, ex, state, broker = stop_setup()
    ex.refuse_stop = True
    demo.step(state["ledger"], broker, ex, ex.rows[-1][0] + HOUR, pairs=["BTC/USDT"])
    assert state["ledger"]["positions"]["BTC/USDT"]["stop_order"] is None
    assert "stop order refused" in state["errors"][0]


def test_replay_stop_triggers_inside_the_candle():
    ex = replay.ReplayExchange({"X/USDT": [[0, 100, 100, 100, 100, 1], [H, 100, 101, 91, 95, 1], [2 * H, 90, 93, 88, 92, 1],
                                           [3 * H, 85, 86, 80, 81, 1], [4 * H, 82, 92, 82, 90, 1], [5 * H, 90, 90, 90, 90, 1]]},
                               fee=0.001)  # fmt: skip
    ex.now_ms = H
    o = ex.create_order("X/USDT", "limit", "sell", 1, 91.08, {"stopLossPrice": 92.0})
    ex.now_ms = 2 * H
    f = ex.fetch_order(o["id"], "X/USDT")  # candle H: opened 100 > stop, low 91 <= 92 -> filled AT the stop
    assert f["status"] == "closed" and f["average"] == 92.0 and f["lastTradeTimestamp"] == H
    o = ex.create_order("X/USDT", "limit", "sell", 1, 89.1, {"stopLossPrice": 90.0})  # placed in candle 2H
    ex.now_ms = 3 * H
    assert ex.fetch_order(o["id"], "X/USDT")["average"] == 90.0  # opened 90 = stop -> at the stop
    o = ex.create_order("X/USDT", "limit", "sell", 1, 86.13, {"stopLossPrice": 87.0})  # placed in candle 3H
    ex.now_ms = 4 * H
    assert ex.fetch_order(o["id"], "X/USDT")["status"] == "open"  # gapped below the limit: waits
    ex.now_ms = 5 * H
    g = ex.fetch_order(o["id"], "X/USDT")  # candle 4H climbs back to the limit -> filled at the limit
    assert g["status"] == "closed" and g["average"] == 86.13 and g["lastTradeTimestamp"] == 4 * H


def test_real_ccxt_demo_switch_passes_the_guard_and_live_fails():
    """Against the installed ccxt (no network, no keys): enable_demo_trading(True) points every
    Binance api url at demo-*.binance.com, and the guard refuses a plain (live) object."""
    ccxt = pytest.importorskip("ccxt")
    live = ccxt.binance()
    with pytest.raises(demo.DemoRefused):
        demo.assert_demo_urls(live)
    d = ccxt.binance()
    d.enable_demo_trading(True)
    demo.assert_demo_urls(d)
    assert d.urls["api"]["private"].startswith("https://demo-api.binance.com/")


def test_demo_broker_loads_markets_before_the_first_order():
    """Found 2026-11-02 against the real ccxt 4.5.90: amount_to_precision raises "markets not loaded"
    on a fresh exchange. The broker's exchange never fetches candles (that is the keyless data
    exchange), so the broker must load the market list itself."""
    ex = FakeExchange({"options": {"defaultType": "spot"}})
    ex.enable_demo_trading(True)
    with pytest.raises(RuntimeError, match="markets not loaded"):
        ex.amount_to_precision("BTC/USDT", 0.1)
    demo.DemoBroker(ex, {}, sleep=lambda s: None)
    assert ex.markets is not None and ex.amount_to_precision("BTC/USDT", 0.123456) == "0.12346"


def test_real_ccxt_needs_markets_for_precision():
    ccxt = pytest.importorskip("ccxt")
    e = ccxt.binance()
    e.enable_demo_trading(True)
    with pytest.raises(ccxt.ExchangeError, match="markets not loaded"):
        e.amount_to_precision("BTC/USDT", 0.1)


def test_too_small_orders_are_recorded_not_sent():
    m = {"limits": {"amount": {"min": 0.001}, "cost": {"min": 5.0}}}
    assert demo.too_small(m, 0.01, 1000.0) is None
    assert "below the minimum 0.001" in demo.too_small(m, 0.0005, 100000.0)
    assert "order value 4.00" in demo.too_small(m, 0.004, 1000.0)
    assert demo.too_small({}, 0.0, 10.0) is not None and demo.too_small({}, 1.0, 10.0) is None
    ex = FakeExchange({"options": {"defaultType": "spot"}})
    ex.enable_demo_trading(True)
    state = {}
    b = demo.DemoBroker(ex, state, sleep=lambda s: None)
    fill = b._order("BTC/USDT", "sell", "exit", 0.00004, 80000.0)  # 3.2 USDT of dust
    assert fill == {"filled": 0.0, "price": 0.0, "fee_usdt": 0.0} and ex.orders == []  # nothing sent
    assert state["orders"][-1]["status"] == "too_small" and "below the minimum 5.0" in state["orders"][-1]["reason"]
    b._order("BTC/USDT", "buy", "entry", 0.001, 80000.0)  # 80 USDT: sent normally
    assert len(ex.orders) == 1


class NetworkError(Exception):  # stands in for ccxt.NetworkError (matched by class name)
    pass


class RateLimitExceeded(NetworkError):
    pass


def _broker():
    ex = FakeExchange({"options": {"defaultType": "spot"}})
    ex._fees, ex.raise_next, ex.coin_free = {}, [], {}
    ex.enable_demo_trading(True)
    return ex, demo.DemoBroker(ex, {}, sleep=lambda s: None)


def test_late_fill_reads_the_fee_from_the_trades():
    """Real ccxt 4.5.90: a Binance fetch_order result has fee None / fees []. A limit order that fills
    after a few polls must still book the fee taken in the coin (or the ledger holds 0.1% too much)."""
    ex, b = _broker()
    ex.plans = [[{"status": "open"}, {"status": "closed", "filled": 1.0, "average": 10.0, "fee": {"cost": 0.001, "currency": "BTC"}}]]
    fill = b.buy("BTC/USDT", 1.0, 10.0)
    assert fill["filled"] == pytest.approx(0.999) and fill["fee_usdt"] == pytest.approx(0.01)


def test_network_errors_while_polling_are_waited_out():
    ex, b = _broker()
    ex.plans = [[{"status": "open"}, {"status": "closed", "filled": 1.0, "average": 10.0}]]
    ex.raise_next = [RateLimitExceeded("429"), NetworkError("timeout")]
    assert b.buy("BTC/USDT", 1.0, 10.0)["filled"] == pytest.approx(1.0)
    ex.raise_next = [ValueError("not a network problem")]
    ex.plans = [[{"status": "open"}, {"status": "closed", "filled": 1.0, "average": 10.0}]]
    with pytest.raises(ValueError):
        b.buy("BTC/USDT", 1.0, 10.0)
    assert demo.is_network_error(RateLimitExceeded()) and not demo.is_network_error(ValueError())


def test_sell_never_exceeds_the_free_coin():
    ex, b = _broker()
    ex.coin_free = {"BTC": 0.999}  # 0.1% went to the fee on the buy
    b.sell("BTC/USDT", 1.0, 10.0)
    assert ex.orders[-1]["amount"] == pytest.approx(0.999)
    ex.coin_free = {}
    b.sell("BTC/USDT", 0.5, 10.0)  # balance not reported: the amount is left alone
    assert ex.orders[-1]["amount"] == pytest.approx(0.5)


def test_demo_exchange_corrects_clock_drift():
    ex = demo.demo_exchange(ENV, factory=FakeExchange)
    assert ex.config["options"]["adjustForTimeDifference"] is True and ex.config["options"]["defaultType"] == "spot"
