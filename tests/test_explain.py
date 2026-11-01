"""Tests for scripts/explain.py with a fake sqlite and fake candles."""

import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("pandas")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import explain  # noqa: E402


def fake_ind(close):
    idx = pd.date_range("2026-09-01", periods=len(close), freq="1h", tz="UTC")
    return explain.indicators(pd.Series(np.asarray(close, float), index=idx))


def test_no_trades_tells_what_each_coin_needs():
    down = fake_ind(np.linspace(200, 100, 1000))  # below EMA200
    text = explain.render([pd.DataFrame()], lambda p: down)
    assert "Henüz işlem yok" in text and "BTC: fiyat EMA200'ün %" in text and "önce EMA200 üstüne çıkmalı" in text


def test_next_entry_need_cases():
    assert "altında; önce" in explain.next_entry_need(pd.Series({"close": 90, "ema200": 100, "ema20": 1, "ema50": 2}))
    assert "yukarı kesmesi bekleniyor" in explain.next_entry_need(pd.Series({"close": 110, "ema200": 100, "ema20": 1, "ema50": 2}))
    assert "zaten yukarı" in explain.next_entry_need(pd.Series({"close": 110, "ema200": 100, "ema20": 3, "ema50": 2}))


def test_closed_trade_explained(tmp_path):
    db = tmp_path / "x.dryrun.sqlite"
    con = sqlite3.connect(db)
    con.execute("create table trades (id int, pair text, is_open int, open_date text, close_date text, open_rate float, "
                "close_rate float, stake_amount float, close_profit float, close_profit_abs float, exit_reason text, "
                "strategy text, fee_open_cost float, fee_close_cost float)")
    con.execute("insert into trades values (1,'BTC/USDT',0,'2026-10-20 10:00:00','2026-10-21 10:00:00',100,110,125,0.097,12.1,"
                "'exit_signal','TrendEmaVolTarget',0.19,0.21)")
    con.commit()
    con.close()
    trades = explain.read_trades(db)
    ind = fake_ind(np.linspace(80, 120, 1500))
    text = explain.render([trades], lambda p: ind)
    for must in ("#1 BTC/USDT", "Neden aldı", "Pozisyon boyutu", "Yatırılan: 125.00", "~10.00 USDT",
                 "EMA20, EMA50'yi aşağı kesti", "+9.70% = +12.10 USDT", "komisyon 0.40", "sadece tutmak"):
        assert must in text


def test_db_opened_read_only():
    src = (Path(__file__).resolve().parent.parent / "scripts" / "explain.py").read_text()
    assert "mode=ro" in src
