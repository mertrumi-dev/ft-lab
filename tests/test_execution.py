"""Tests for scripts/execution.py on a tiny fake Freqtrade sqlite DB."""

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import execution  # noqa: E402


def make_db(path, orders, fees=(0.15, 0.16)):
    con = sqlite3.connect(path)
    con.execute("create table orders (ft_pair text, side text, ft_order_side text, status text, ft_price float, "
                "average float, price float, filled float, order_date text, order_filled_date text)")
    con.execute("create table trades (fee_open_cost float, fee_close_cost float)")
    con.executemany("insert into orders values (?,?,?,?,?,?,?,?,?,?)", orders)
    con.execute("insert into trades values (?,?)", fees)
    con.commit()
    con.close()


T0 = datetime(2026, 11, 2, 10, 5, tzinfo=timezone.utc)


def prices(pair, when):
    # signal candle 09:00 closes at 100; first candle after +1h (12:00) -> 101; next day -> 110
    table = {datetime(2026, 11, 2, 9, tzinfo=timezone.utc): 100.0,
             datetime(2026, 11, 2, 12, tzinfo=timezone.utc): 101.0}
    for t, v in sorted(table.items()):
        if t >= when:
            return v
    return 110.0


def test_empty_db_prints_no_orders(tmp_path):
    db = tmp_path / "x.dryrun.sqlite"
    make_db(db, [], fees=(None, None))
    orders, fees = execution.read_orders(db)
    s = execution.summarize(orders, fees, prices)
    assert s["orders"] == 0 and "no orders yet" in execution.render("x", s)


def test_fill_slippage_wait_and_missed_entry(tmp_path):
    db = tmp_path / "x.dryrun.sqlite"
    f = lambda d: d.strftime("%Y-%m-%d %H:%M:%S")  # noqa: E731
    make_db(db, [
        ("BTC/USDT", "buy", "entry", "closed", 100.0, 100.2, 100.0, 1.0, f(T0), f(T0 + timedelta(minutes=4))),
        ("BTC/USDT", "buy", "entry", "canceled", 100.0, None, 100.0, 0.0, f(T0), None),
    ])
    orders, fees = execution.read_orders(db)
    s = execution.summarize(orders, fees, prices)
    assert s["entries"] == 2 and s["missed_entries"] == 1 and s["fill_rate_entries"] == pytest.approx(0.5)
    assert s["avg_slippage"] == pytest.approx(0.002)  # paid 100.2 vs signal close 100
    assert s["avg_minutes_to_fill"] == pytest.approx(4.0)
    assert s["missed_move_1h"] == pytest.approx(0.01) and s["missed_move_24h"] == pytest.approx(0.10)
    assert s["fees"] == pytest.approx(0.31)


def test_db_is_opened_read_only(tmp_path):
    db = tmp_path / "x.dryrun.sqlite"
    make_db(db, [])
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    with pytest.raises(sqlite3.OperationalError):
        con.execute("insert into trades values (1, 1)")
    src = (Path(__file__).resolve().parent.parent / "scripts" / "execution.py").read_text()
    assert "mode=ro" in src


def test_sell_slippage_sign():
    assert execution.slippage("sell", 100, 99) == pytest.approx(100 / 99 - 1)  # got less = worse = positive
    assert execution.signal_candle(datetime(2026, 1, 1, 10, 30, tzinfo=timezone.utc)).hour == 9
