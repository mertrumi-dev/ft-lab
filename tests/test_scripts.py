"""Tests for the measuring tools: data slices, benchmark math, safe wrapper."""

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import benchmark  # noqa: E402
import ft  # noqa: E402
from splits import SLICES, compute_slices  # noqa: E402


# --- slices ------------------------------------------------------------------


def test_slices_are_back_to_back_and_cover_everything():
    s = compute_slices(date(2020, 1, 1), date(2025, 1, 1))
    assert s["train"].start == date(2020, 1, 1)
    assert s["train"].end == s["validation"].start
    assert s["validation"].end == s["test"].start
    assert s["test"].end == date(2025, 1, 1)


def test_test_slice_is_last_20_percent():
    total = (SLICES["test"].end - SLICES["train"].start).days
    test_days = (SLICES["test"].end - SLICES["test"].start).days
    assert test_days / total == pytest.approx(0.2, abs=0.01)


def test_timerange_format():
    s = compute_slices(date(2021, 1, 1), date(2021, 11, 1))["train"]
    assert s.timerange == f"{s.start:%Y%m%d}-{s.end:%Y%m%d}"


# --- benchmark math ------------------------------------------------------------


def series(values, start="2024-01-01"):
    idx = pd.date_range(start, periods=len(values), freq="1D", tz="UTC")
    return pd.Series(values, index=idx, dtype=float)


def test_buy_and_hold_doubles_without_fee():
    eq = benchmark.buy_and_hold_equity({"A": series([100, 150, 200])}, fee=0.0)
    assert eq.iloc[-1] == pytest.approx(2.0)


def test_buy_and_hold_pays_fee_on_both_sides():
    eq = benchmark.buy_and_hold_equity({"A": series([100, 100])}, fee=0.01)
    assert eq.iloc[-1] == pytest.approx(0.99 * 0.99)


def test_buy_and_hold_equal_weight():
    # A doubles, B stays flat -> portfolio +50%
    eq = benchmark.buy_and_hold_equity(
        {"A": series([100, 200]), "B": series([50, 50])}, fee=0.0
    )
    assert eq.iloc[-1] == pytest.approx(1.5)


def test_max_drawdown():
    # 1 -> 2 (peak) -> 1 -> 1.5: worst fall is 50%
    assert benchmark.max_drawdown(series([1, 2, 1, 1.5])) == pytest.approx(0.5)


def test_summarize_calmar():
    # +100% over ~2 years with 50% drawdown
    idx = pd.date_range("2022-01-01", "2024-01-01", freq="1D", tz="UTC")
    values = np.linspace(1, 2, len(idx))
    values[len(idx) // 2] = values[len(idx) // 2 - 1] * 0.5
    r = benchmark.summarize(pd.Series(values, index=idx))
    assert r["total_return"] == pytest.approx(1.0)
    assert r["calmar"] == pytest.approx(r["cagr"] / r["max_drawdown"])


def test_benchmark_reads_feather_and_respects_slice(tmp_path):
    name = "train"
    s = SLICES[name]
    idx = pd.date_range(s.start, s.end, freq="1h", tz="UTC", inclusive="left")
    for pair in ["BTC_USDT", "ETH_USDT", "SOL_USDT", "BNB_USDT", "XRP_USDT"]:
        df = pd.DataFrame({"date": idx, "open": 1.0, "high": 1.0, "low": 1.0,
                           "close": np.linspace(100, 200, len(idx)), "volume": 1.0})
        df.to_feather(tmp_path / f"{pair}-1h.feather")
    r = benchmark.run(name, "1h", fee=0.0, data_dir=tmp_path)
    assert r["total_return"] == pytest.approx(1.0, rel=1e-3)
    assert r["max_drawdown"] == pytest.approx(0.0)


# --- safe wrapper ---------------------------------------------------------------


def cmds(*argv):
    return ft.build_commands(ft.parse_args(list(argv)))


def cmd(*argv):
    commands = cmds(*argv)
    assert len(commands) == 1
    return commands[0]


def test_backtest_uses_slice_dates_and_fee():
    c = cmd("backtest", "--slice", "validation")
    assert c[c.index("--timerange") + 1] == SLICES["validation"].timerange
    assert c[c.index("--fee") + 1] == "0.0015"


def test_test_slice_refused_without_flag():
    with pytest.raises(SystemExit):
        cmd("backtest", "--slice", "test")


def test_test_slice_allowed_with_flag():
    c = cmd("backtest", "--slice", "test", "--final-test")
    assert c[c.index("--timerange") + 1] == SLICES["test"].timerange


def test_hyperopt_always_train():
    c = cmd("hyperopt")
    assert c[c.index("--timerange") + 1] == SLICES["train"].timerange


def test_protections_always_simulated():
    assert "--enable-protections" in cmd("backtest", "--slice", "train")
    assert "--enable-protections" in cmd("hyperopt")


def test_backtest_compares_several_strategies():
    c = cmd("backtest", "--slice", "train", "--strategy", "TrendEma", "TrendEmaAtr")
    i = c.index("--strategy-list")
    assert c[i + 1 : i + 3] == ["TrendEma", "TrendEmaAtr"]


def test_strategies_grouped_by_timeframe():
    commands = cmds("backtest", "--slice", "train", "--strategy", "TrendEma", "TrendEma4h", "TrendBreakout")
    by_tf = {c[c.index("--timeframe") + 1]: c for c in commands}
    assert set(by_tf) == {"1h", "4h"}
    assert "TrendEma4h" in by_tf["4h"] and "TrendEma4h" not in by_tf["1h"]
    assert "TrendBreakout" in by_tf["1h"]


def test_timeframe_map_matches_strategies():
    pytest.importorskip("freqtrade")
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "user_data" / "strategies"))
    import trend_variants

    for name, tf in ft.STRATEGY_TIMEFRAMES.items():
        assert getattr(trend_variants, name).timeframe == tf
    assert trend_variants.TrendEmaAtr.timeframe == "1h"


def test_all_expands_to_every_strategy():
    commands = cmds("backtest", "--slice", "train", "--strategy", "all")
    named = [x for c in commands for x in c if x in ft.ALL_STRATEGIES]
    assert sorted(named) == sorted(ft.ALL_STRATEGIES)


def test_benchmark_runs_in_docker_with_slice():
    c = cmd("benchmark", "--slice", "validation")
    assert c[:3] == ["docker", "compose", "run"]
    assert c[c.index("--slice") + 1] == "validation"


# --- report ---------------------------------------------------------------------

import report  # noqa: E402

BH = {"total_return": 2.0, "cagr": 0.5, "max_drawdown": 0.6, "calmar": 0.5 / 0.6}


def fake_stats(trades=80, cagr=0.2, mdd=0.1, wins=40):
    return {"total_trades": trades, "profit_total": 0.7, "cagr": cagr,
            "max_drawdown_account": mdd, "wins": wins, "profit_factor": 1.4}


def test_report_row_calmar_is_cagr_over_drawdown():
    row = report.strategy_row("X", fake_stats(cagr=0.2, mdd=0.1))
    assert row["calmar"] == pytest.approx(2.0)
    assert row["win_rate"] == pytest.approx(0.5)


def test_verdict_pass_and_each_failure():
    assert report.verdict(report.strategy_row("X", fake_stats()), BH) == "PASS"
    assert "trades" in report.verdict(report.strategy_row("X", fake_stats(trades=10)), BH)
    assert "Calmar" in report.verdict(report.strategy_row("X", fake_stats(cagr=0.05, mdd=0.1)), BH)
    assert "DD" in report.verdict(report.strategy_row("X", fake_stats(cagr=0.5, mdd=0.35)), BH)


def test_table_has_benchmark_and_strategies():
    rows = [report.strategy_row("A", fake_stats()), report.strategy_row("B", fake_stats(cagr=0.1))]
    text = report.format_table(rows, BH)
    names = [line.split()[0] for line in text.splitlines()[2:]]
    assert names == ["BUY", "A", "B"]  # benchmark first, then best Calmar first
