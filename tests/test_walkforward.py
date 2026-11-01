"""Tests for the walk-forward check (pick on the past, trade the future)."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import ft  # noqa: E402
import walkforward as wf  # noqa: E402

UTC = "UTC"


def series(points):
    """{"2021-03-01": 0.05, ...} -> trade returns indexed by close time."""
    idx = pd.DatetimeIndex([pd.Timestamp(d, tz=UTC) for d in points])
    return pd.Series(list(points.values()), index=idx, dtype=float)


def test_windows_cover_the_period_without_gaps_and_cut_at_end():
    w = wf.windows(pd.Timestamp("2022-01-01", tz=UTC), pd.Timestamp("2023-03-01", tz=UTC), 6)
    assert [(a.date().isoformat(), b.date().isoformat()) for a, b in w] == [
        ("2022-01-01", "2022-07-01"), ("2022-07-01", "2023-01-01"), ("2023-01-01", "2023-03-01"),
    ]  # fmt: skip


def test_growth_and_drawdown_of_chained_trades():
    r = pd.Series([0.10, -0.50, 0.20])
    assert wf.growth(r) == pytest.approx(1.1 * 0.5 * 1.2 - 1)
    assert wf.closed_drawdown(r) == pytest.approx(0.5)
    assert wf.growth(pd.Series(dtype=float)) == 0.0


def test_trade_series_uses_balance_before_each_trade():
    trades = [
        {"close_date": "2021-02-01 00:00:00+00:00", "profit_abs": 100.0},
        {"close_date": "2021-01-01 00:00:00+00:00", "profit_abs": 100.0},
    ]
    s = wf.trade_series(trades, 1000.0)
    assert list(s.round(6)) == [0.1, round(100 / 1100, 6)]  # sorted by close date
    assert str(s.index.tz) == "UTC"


def test_choice_uses_only_the_past_never_the_window_it_trades():
    # A shines in 2021 then fails; B is quiet in 2021 then shines.
    a = series({"2021-03-01": 0.30, "2021-09-01": 0.30, "2022-03-01": -0.20})
    b = series({"2021-03-01": 0.01, "2021-09-01": 0.01, "2022-03-01": 0.50})
    r = wf.walk_forward({"A": a, "B": b}, pd.Timestamp("2021-01-01", tz=UTC),
                        pd.Timestamp("2022-07-01", tz=UTC), fixed="B")  # fmt: skip
    first = r["rows"][0]
    assert first["chosen"] == "A"  # best on 2021, even though B wins in 2022
    assert first["chosen_return"] == pytest.approx(-0.20)
    assert first["fixed_return"] == pytest.approx(0.50)
    assert r["fixed"]["return"] > r["picked"]["return"]


def test_tie_keeps_the_fixed_rule():
    same = series({"2021-03-01": 0.10})
    r = wf.walk_forward({"A": same, "TrendEma": same.copy()}, pd.Timestamp("2021-01-01", tz=UTC),
                        pd.Timestamp("2022-07-01", tz=UTC), fixed="TrendEma")  # fmt: skip
    assert r["rows"][0]["chosen"] == "TrendEma"


def test_ft_walkforward_is_train_only_and_reads_no_kill_results():
    with pytest.raises(SystemExit):
        ft.parse_args(["walkforward", "--slice", "validation"])
    with pytest.raises(SystemExit):
        ft.parse_args(["walkforward", "--slice", "test"])
    (cmd,) = ft.build_commands(ft.parse_args(["walkforward", "--slice", "train", "--no-kill-switch"]))
    assert "/freqtrade/scripts/walkforward.py" in cmd
    assert f"/freqtrade/{ft.NO_KILL_DIR}" in cmd
    assert "EmaSlow60" in cmd and "TrendEma" in cmd
