"""Tests for the hourly (mark-to-market) equity curve."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import equity  # noqa: E402
import report  # noqa: E402

IDX = pd.date_range("2022-01-01", periods=6, freq="1h", tz="UTC")


def trade(open_i, close_i, amount, stake, profit, pair="BTC/USDT"):
    return {"pair": pair, "open_date": str(IDX[open_i]), "close_date": str(IDX[close_i]),
            "amount": amount, "stake_amount": stake, "profit_abs": profit}


def test_open_trade_dip_is_visible_hourly():
    # buy 1 coin at 100 with 100 USDT; price dips to 70, closes at 98 -> -2 realized
    closes = {"BTC/USDT": pd.Series([100, 85, 70, 90, 98, 98], index=IDX, dtype=float)}
    curve = equity.hourly_equity([trade(0, 4, 1.0, 100.0, -2.0)], closes, 1000.0, IDX)
    assert list(curve["equity"]) == [1000, 985, 970, 990, 998, 998]
    # closed-trade view would say 0.2% drawdown; hourly view sees 3%
    assert equity.max_drawdown(curve["equity"]) == pytest.approx(0.03)


def test_exposure_is_share_of_money_in_coins():
    closes = {"BTC/USDT": pd.Series([100.0] * 6, index=IDX)}
    curve = equity.hourly_equity([trade(0, 3, 2.5, 250.0, 0.0)], closes, 1000.0, IDX)
    # in coins for 3 of 6 hours, 25% each time -> 12.5% on average
    assert equity.summary(curve)["exposure"] == pytest.approx(0.125)


def test_two_pairs_add_up_and_missing_prices_are_ignored():
    closes = {"BTC/USDT": pd.Series([100.0, 110, 110, 110, 110, 110], index=IDX),
              "ETH/USDT": pd.Series([10.0, 10, 5, 5, 5, 5], index=IDX)}
    trades = [trade(0, 5, 1.0, 100.0, 10.0), trade(1, 5, 10.0, 100.0, -50.0, "ETH/USDT"),
              trade(0, 2, 1.0, 1.0, 0.0, "XXX/USDT")]
    curve = equity.hourly_equity(trades, closes, 1000.0, IDX)
    assert curve["equity"].iloc[2] == pytest.approx(1000 + 10 - 50)
    assert curve["equity"].iloc[5] == pytest.approx(1000 + 10 - 50)  # both closed, realized


def test_report_uses_hourly_drawdown_for_calmar_but_closed_for_kill_switch():
    stats = {"total_trades": 80, "profit_total": 0.5, "cagr": 0.3, "max_drawdown_account": 0.10,
             "wins": 30, "profit_factor": 1.5}
    row = report.strategy_row("X", stats, {"max_drawdown_hourly": 0.25, "exposure": 0.3})
    assert row["calmar"] == pytest.approx(0.3 / 0.25)
    assert row["exposure"] == 0.3
    bh = {"calmar": 0.5, "max_drawdown": 0.9}
    assert "kill switch" not in report.verdict(row, bh)  # closed DD 10% < 20%


def _ms(i):
    return int(IDX[i].timestamp() * 1000)


def test_order_based_curve_handles_partial_sells():
    # buy 2 coins at 100, sell 1 at 120 (hour 2), sell the last at 90 (hour 4); no fees
    closes = {"BTC/USDT": pd.Series([100.0, 110, 120, 100, 90, 90], index=IDX)}
    t = {"pair": "BTC/USDT", "fee_open": 0.0, "fee_close": 0.0, "orders": [
        {"order_filled_timestamp": _ms(0), "ft_is_entry": True, "amount": 2.0, "cost": 200.0},
        {"order_filled_timestamp": _ms(2), "ft_is_entry": False, "amount": 1.0, "cost": 120.0},
        {"order_filled_timestamp": _ms(4), "ft_is_entry": False, "amount": 1.0, "cost": 90.0},
    ]}
    curve = equity.build_curve([t], closes, 1000.0, IDX)
    assert list(curve["equity"]) == [1000, 1020, 1040, 1020, 1010, 1010]
    assert list(curve["invested"]) == [200, 220, 120, 100, 0, 0]


def test_order_based_curve_charges_fees():
    closes = {"BTC/USDT": pd.Series([100.0] * 6, index=IDX)}
    t = {"pair": "BTC/USDT", "fee_open": 0.01, "fee_close": 0.01, "orders": [
        {"order_filled_timestamp": _ms(0), "ft_is_entry": True, "amount": 1.0, "cost": 100.0},
        {"order_filled_timestamp": _ms(3), "ft_is_entry": False, "amount": 1.0, "cost": 100.0},
    ]}
    curve = equity.build_curve([t], closes, 1000.0, IDX)
    assert curve["equity"].iloc[-1] == pytest.approx(1000 - 1 - 1)
