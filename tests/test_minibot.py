"""Tests for the from-scratch mini bot (Phase 4, paper trading only)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from minibot import bot, paper, signals  # noqa: E402

HOUR = 3_600_000


def test_ema_matches_pandas():
    values = list(np.random.default_rng(3).normal(100, 5, 300))
    expected = pd.Series(values).ewm(span=20, adjust=False).mean()
    assert signals.ema(values, 20) == pytest.approx(list(expected))


def test_signal_agrees_with_the_freqtrade_strategy():
    pytest.importorskip("freqtrade")
    sys.path.insert(0, str(ROOT / "user_data" / "strategies"))
    import trend_ema

    rng = np.random.default_rng(7)
    close = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, 3000)))
    df = pd.DataFrame({"close": close, "volume": 1.0})
    strat = trend_ema.TrendEma({})
    df = strat.populate_indicators(df, {})
    df = strat.populate_exit_trend(strat.populate_entry_trend(df, {}), {})
    checked = 0
    for i in range(400, len(close)):
        sig = signals.signal(list(close[: i + 1]))
        assert (sig == "buy") == (df["enter_long"].iloc[i] == 1)
        assert (sig == "sell") == (df["exit_long"].iloc[i] == 1)
        checked += sig != "hold"
    assert checked > 10  # the data really produced signals


def test_no_signal_before_warm_up():
    assert signals.signal([100.0] * 399) == "hold"


def test_stake_is_one_percent_risk_capped_at_25_percent():
    acc = paper.new_account(1000)
    assert paper.stake_for(acc, {}) == pytest.approx(125.0)  # 1000 * 1% / 8%


def test_buy_then_sell_pays_fee_twice():
    acc = paper.new_account(1000)
    paper.buy(acc, "BTC/USDT", 100.0, {}, "t0")
    assert acc["cash"] == pytest.approx(875.0)
    paper.sell(acc, "BTC/USDT", 100.0, "t1", "test")
    assert acc["cash"] == pytest.approx(875 + 125 * (1 - paper.FEE) ** 2)
    assert acc["closed"][0]["profit"] < 0  # flat price still loses the fees


def test_only_one_position_per_coin():
    acc = paper.new_account(1000)
    assert paper.buy(acc, "BTC/USDT", 100.0, {}, "t0")
    assert paper.buy(acc, "BTC/USDT", 100.0, {}, "t1") is None


def test_kill_switch_blocks_new_buys_after_20_percent_realized_fall():
    acc = paper.new_account(1000)
    acc["realized"] = 799.0
    note = paper.buy(acc, "BTC/USDT", 100.0, {}, "t0")
    assert "KILL SWITCH" in note and not acc["positions"]


def test_stop_uses_candle_low():
    acc = paper.new_account(1000)
    paper.buy(acc, "BTC/USDT", 100.0, {}, "t0")
    assert not paper.stop_hit(acc, "BTC/USDT", 92.1)
    assert paper.stop_hit(acc, "BTC/USDT", 92.0)


class FakeExchange:
    def __init__(self, rows):
        self.rows = rows

    def fetch_ohlcv(self, pair, timeframe, limit):
        return self.rows[-limit:]


def rows_from(closes, lows=None, start=0):
    lows = lows or closes
    return [[start + i * HOUR, c, c, lo, c, 1.0] for i, (c, lo) in enumerate(zip(closes, lows))]


def test_unfinished_candle_is_ignored():
    rows = rows_from([1.0] * 5)
    now = rows[-1][0] + HOUR // 2  # last candle is half way through its hour
    assert len(bot.closed_candles(FakeExchange(rows), "X", now)) == 4


def test_step_sells_at_the_stop_price():
    acc = paper.new_account(1000)
    paper.buy(acc, "BTC/USDT", 100.0, {}, "t0")
    rows = rows_from([100.0] * 10, lows=[100.0] * 9 + [90.0])
    log = bot.step(acc, FakeExchange(rows), rows[-1][0] + HOUR, pairs=["BTC/USDT"])
    assert "stoploss" in log[0] and "@ 92.0000" in log[0]
    assert not acc["positions"]


def test_state_survives_save_and_load(tmp_path):
    acc = paper.new_account(1000)
    paper.buy(acc, "BTC/USDT", 100.0, {}, "t0")
    path = tmp_path / "state.json"
    bot.save_state(acc, path)
    assert bot.load_state(path) == acc


def test_exchange_has_no_keys():
    pytest.importorskip("ccxt")
    ex = bot.public_exchange()  # building the object does not touch the network
    assert not ex.apiKey and not ex.secret


def test_minibot_source_never_sets_keys():
    for path in (ROOT / "minibot").glob("*.py"):
        text = path.read_text()
        for word in ("apiKey\":", "secret\":", "'apiKey'", "\"secret\"", "dry_run"):
            assert word not in text, f"{path.name} mentions {word}"
