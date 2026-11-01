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
    assert paper.TRADABLE_BALANCE_RATIO == 0.99  # read from user_data/config/config.json
    assert paper.stake_for(acc, {}) == pytest.approx(123.75)  # 1000 x 0.99 x 1% / 8%


def test_buy_then_sell_pays_fee_twice():
    acc = paper.new_account(1000)
    paper.buy(acc, "BTC/USDT", 100.0, {}, "t0")
    assert acc["cash"] == pytest.approx(1000 - 123.75)
    paper.sell(acc, "BTC/USDT", 100.0, "t1", "test")
    assert acc["cash"] == pytest.approx(1000 - 123.75 + 123.75 * (1 - paper.FEE) ** 2)
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
    # demo.py is the one module that passes keys to ccxt; tests/test_minibot_demo.py checks
    # that it takes them only from the FTLAB_DEMO_* environment variables.
    for path in (ROOT / "minibot").glob("*.py"):
        if path.name == "demo.py":
            continue
        text = path.read_text()
        for word in ("apiKey\":", "secret\":", "'apiKey'", "\"secret\"", "dry_run"):
            assert word not in text, f"{path.name} mentions {word}"


def test_realized_vol_matches_pandas_and_sizing():
    rng = np.random.default_rng(11)
    close = list(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 900))))
    expected = np.log(pd.Series(close)).diff().rolling(signals.VOL_WINDOW).std() * np.sqrt(signals.HOURS_PER_YEAR)
    assert signals.realized_vol(close) == pytest.approx(expected.iloc[-1])
    assert np.isnan(signals.realized_vol(close[:720]))  # 719 returns: not enough yet
    assert signals.vol_scale(float("nan")) == 1.0 and signals.vol_scale(1.2) == pytest.approx(0.5)
    assert signals.vol_scale(0.3) == 1.0  # never above the normal stake


def test_voltarget_parity_with_the_freqtrade_strategy():
    """Same candles -> same entries, exits AND stake as TrendEmaVolTarget (populate_* + custom_stake_amount)."""
    pytest.importorskip("freqtrade")
    sys.path.insert(0, str(ROOT / "user_data" / "strategies"))
    import sizing

    rng = np.random.default_rng(7)
    sigma = np.r_[np.full(1500, 0.005), np.full(1500, 0.012)]  # calm coin, then a wild one
    close = 100 * np.exp(np.cumsum(rng.normal(0.0003, sigma)))
    strat = sizing.TrendEmaVolTarget({})
    df = strat.populate_indicators(pd.DataFrame({"close": close, "volume": 1.0}), {})
    df = strat.populate_exit_trend(strat.populate_entry_trend(df, {}), {})

    class Wallets:
        def get_total_stake_amount(self):  # Freqtrade: (tied + free) x tradable_balance_ratio
            return 1000.0 * paper.TRADABLE_BALANCE_RATIO

    class Dp:
        i = 0

        def get_analyzed_dataframe(self, pair, timeframe):
            return df.iloc[: self.i + 1], None

    strat.wallets, strat.dp = Wallets(), Dp()
    scales, entries = set(), 0
    for i in range(400, len(close)):
        prefix = list(close[: i + 1])
        sig = signals.signal(prefix)
        assert (sig == "buy") == (df["enter_long"].iloc[i] == 1)
        assert (sig == "sell") == (df["exit_long"].iloc[i] == 1)
        if sig == "buy" or i % 50 == 0:  # every entry plus a sample of other hours
            scale = signals.vol_scale(signals.realized_vol(prefix))
            strat.dp.i = i
            ft_stake = strat.custom_stake_amount("X", None, 1, 0, None, 10_000, 1, None, "long")
            assert paper.stake_for(paper.new_account(1000), {}, scale) == pytest.approx(ft_stake)
            scales.add(round(scale, 2))
            entries += sig == "buy"
    assert entries > 5 and min(scales) < 0.8 and max(scales) == 1.0  # both full and shrunk sizes were checked


def test_step_voltarget_sizes_the_buy_and_trendema_mode_does_not():
    rng = np.random.default_rng(7)
    full = list(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, 4000))))
    # the first 1000-candle window (what the bot fetches) whose last closed candle is a buy
    close = next(full[i - 999 : i + 1] for i in range(999, len(full)) if signals.signal(full[i - 999 : i + 1]) == "buy")
    rows = rows_from(close)
    now = rows[-1][0] + HOUR
    a, b = paper.new_account(1000), paper.new_account(1000)
    bot.step(a, FakeExchange(rows), now, pairs=["BTC/USDT"])
    bot.step(b, FakeExchange(rows), now, pairs=["BTC/USDT"], rule="trendema")
    expected = 123.75 * signals.vol_scale(signals.realized_vol(close))  # 1000 x 0.99 x 1% / 8% = 123.75
    assert expected < 123.75  # a wild coin (sigma 1.2%/h ~ 110%/yr): smaller than the normal stake
    assert a["positions"]["BTC/USDT"]["stake"] == pytest.approx(expected)
    assert b["positions"]["BTC/USDT"]["stake"] == pytest.approx(123.75)
