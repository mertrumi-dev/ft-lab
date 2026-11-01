"""Tests for the trade analysis script."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import analyze  # noqa: E402
import ft  # noqa: E402


def trade(pair, open_, close, profit, reason):
    return {"pair": pair, "open_date": open_, "close_date": close, "profit_abs": profit * 10,
            "profit_ratio": profit, "exit_reason": reason}  # fmt: skip


TRADES = [
    trade("BTC/USDT", "2021-01-01 00:00", "2021-01-01 03:00", 0.10, "exit_signal"),
    trade("BTC/USDT", "2021-02-01 00:00", "2021-02-03 00:00", -0.08, "stop_loss"),
    trade("ETH/USDT", "2022-01-01 00:00", "2022-01-10 00:00", -0.02, "exit_signal"),
]


def test_group_by_exit_reason_counts_and_sums():
    t = analyze.group_table(analyze.trades_frame(TRADES), "exit_reason")
    assert t.loc["stop_loss", "trades"] == 1 and t.loc["stop_loss", "win%"] == 0
    assert t.loc["exit_signal", "total_usdt"] == pytest.approx(0.8)
    assert t.loc["exit_signal", "win%"] == 50


def test_holding_time_buckets():
    df = analyze.trades_frame(TRADES)
    assert list(df["hold"].astype(str)) == ["<6h", "1-3d", "1-2w"]


def test_concentration_of_profit():
    trades = [trade("X", "2021-01-01", "2021-01-02", p, "exit_signal") for p in (0.5, 0.1, 0.1, 0.1, -0.3)]
    # total = 5 + 1 + 1 + 1 - 3 = 5 USDT; the best trade alone made 5 -> 100%
    assert analyze.concentration(analyze.trades_frame(trades), top=0.2) == pytest.approx(1.0)


def test_ft_analyze_is_train_only():
    with pytest.raises(SystemExit):
        ft.parse_args(["analyze", "--slice", "validation"])
    (cmd,) = ft.build_commands(ft.parse_args(["analyze", "--slice", "train", "--no-kill-switch"]))
    assert "/freqtrade/scripts/analyze.py" in cmd and "TrendEma" in cmd
