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
    import dip_rsi
    import donchian_ensemble
    import regime
    import sma_daily
    import trend_variants

    import sizing

    modules = [trend_variants, donchian_ensemble, dip_rsi, sma_daily, regime, sizing]
    for name, tf in ft.STRATEGY_TIMEFRAMES.items():
        if name in ft.THIRD_PARTY:
            continue  # third-party code is not imported in tests (checked in test_benchmark_bots)
        cls = next(getattr(m, name) for m in modules if hasattr(m, name))
        assert cls.timeframe == tf
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


# --- robustness: other coins, double fee ------------------------------------------

from universe import WIDE_2021  # noqa: E402


def test_default_backtest_uses_config_pairs_and_normal_fee():
    c = cmd("backtest", "--slice", "train")
    assert "--pairs" not in c
    assert c[c.index("--fee") + 1] == "0.0015"


def test_wide_universe_adds_pairs_and_keeps_slice_lock():
    c = cmd("backtest", "--slice", "train", "--universe", "wide")
    assert c[c.index("--pairs") + 1:] == WIDE_2021
    with pytest.raises(SystemExit):
        cmds("backtest", "--slice", "test", "--universe", "wide")


def test_wide_universe_has_no_core_coins():
    # core and wide must not overlap, so report never mixes their results
    assert not {"BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"} & set(WIDE_2021)


def test_fee_stress_doubles_fee_only_when_asked():
    c = cmd("backtest", "--slice", "train", "--fee-stress")
    assert c[c.index("--fee") + 1] == "0.003"
    r = cmd("report", "--slice", "train", "--fee-stress")
    assert r[r.index("--fee") + 1] == "0.003"


def test_report_only_compares_same_universe_and_fee():
    base = {"timerange": "A", "pairlist": ["BTC/USDT"], "trades": [{"fee_open": 0.0015}]}
    core = ["BTC/USDT", "ETH/USDT"]
    assert report.matches(base, "A", core, 0.0015)
    assert not report.matches(base, "B", core, 0.0015)  # other slice
    assert not report.matches(base, "A", WIDE_2021, 0.0015)  # other coins
    assert not report.matches(base, "A", core, 0.003)  # other fee
    assert not report.matches({**base, "trades": []}, "A", core, 0.0015)  # no trades: unknown fee


def test_wide_benchmark_skips_coins_without_data(tmp_path):
    s = SLICES["train"]
    idx = pd.date_range(s.start, s.end, freq="1h", tz="UTC", inclusive="left")
    for pair in WIDE_2021[:-1]:  # last coin has no file (e.g. delisted)
        df = pd.DataFrame({"date": idx, "open": 1.0, "high": 1.0, "low": 1.0,
                           "close": np.linspace(100, 50, len(idx)), "volume": 1.0})
        df.to_feather(tmp_path / f"{pair.replace('/', '_')}-1h.feather")
    r = benchmark.run("train", "1h", fee=0.0, data_dir=tmp_path, universe="wide")
    assert r["skipped"] == [WIDE_2021[-1]]
    assert r["total_return"] == pytest.approx(-0.5, rel=1e-3)
    with pytest.raises(FileNotFoundError):
        benchmark.run("train", "1h", fee=0.0, data_dir=tmp_path, universe="core")


def test_report_shows_last_trade_and_flags_kill_switch():
    s = {**fake_stats(cagr=0.3, mdd=0.201), "trades": [
        {"close_date": "2021-05-01 10:00:00+00:00"}, {"close_date": "2022-06-19 03:00:00+00:00"}]}
    row = report.strategy_row("X", s)
    assert row["last_trade"] == "2022-06-19"
    assert "kill switch" in report.verdict(row, BH)
    assert "kill switch" not in report.verdict(report.strategy_row("Y", fake_stats(mdd=0.19)), BH)


def test_no_kill_switch_uses_research_config_and_own_folder():
    c = cmd("backtest", "--slice", "train", "--no-kill-switch")
    assert c[c.index("--config", c.index("--config") + 1) + 1].endswith("research-no-kill-switch.json")
    assert c[c.index("--backtest-directory") + 1].endswith("no_kill_switch")
    assert "--config" in cmd("backtest", "--slice", "train") and \
        "--backtest-directory" not in cmd("backtest", "--slice", "train")
    r = cmd("report", "--slice", "train", "--no-kill-switch")
    assert r[r.index("--results-dir") + 1].endswith("no_kill_switch")
    assert "--results-dir" not in cmd("report", "--slice", "train")


def test_no_kill_switch_still_refuses_test_slice():
    with pytest.raises(SystemExit):
        cmds("backtest", "--slice", "test", "--no-kill-switch")


def test_no_kill_switch_report_says_live_bot_would_stop():
    row = report.strategy_row("X", fake_stats(cagr=0.6, mdd=0.23))
    assert "would have stopped" in report.verdict(row, BH, kill_switch_on=False)
    assert "stopped buying" in report.verdict(row, BH, kill_switch_on=True)


# --- year by year -------------------------------------------------------------------


def test_benchmark_by_year_splits_calendar_years():
    idx = pd.to_datetime(["2021-01-01", "2021-12-31", "2022-01-01", "2022-06-01", "2022-12-31"], utc=True)
    eq = pd.Series([1.0, 2.0, 2.0, 1.0, 1.5], index=idx)
    y = benchmark.by_year(eq)
    assert y[2021]["return"] == pytest.approx(1.0)
    assert y[2022]["return"] == pytest.approx(-0.25)
    assert y[2022]["max_drawdown"] == pytest.approx(0.5)


def test_strategy_by_year_compounds_balance():
    stats = {"starting_balance": 1000, "trades": [
        {"close_date": "2021-03-01 00:00:00+00:00", "profit_abs": 100},   # 1000 -> 1100
        {"close_date": "2022-02-01 00:00:00+00:00", "profit_abs": -220},  # 1100 -> 880 (-20%)
        {"close_date": "2022-05-01 00:00:00+00:00", "profit_abs": 110},   # 880 -> 990
    ]}
    y = report.strategy_by_year(stats)
    assert y[2021] == {"trades": 1, "return": pytest.approx(0.10), "max_drawdown": 0.0}
    assert y[2022]["trades"] == 2
    assert y[2022]["return"] == pytest.approx(990 / 1100 - 1)
    assert y[2022]["max_drawdown"] == pytest.approx(0.20)


def test_year_table_marks_years_without_trades():
    stats = {"A": {"starting_balance": 1000, "trades": [
        {"close_date": "2021-03-01 00:00:00+00:00", "profit_abs": 50}]}}
    text = report.format_years(stats, {2021: {"return": 1.0, "max_drawdown": 0.3},
                                       2022: {"return": -0.6, "max_drawdown": 0.7}})
    assert "2022" in text and "no trades" in text


def test_report_by_year_and_strategy_filter_are_passed_on():
    r = cmd("report", "--slice", "train", "--by-year", "--strategy", "TrendEma", "TrendEmaBtc")
    assert "--by-year" in r
    assert r[r.index("--strategy") + 1:r.index("--strategy") + 3] == ["TrendEma", "TrendEmaBtc"]


# --- Monte Carlo ----------------------------------------------------------------

import montecarlo  # noqa: E402


def test_trade_returns_are_share_of_balance():
    trades = [{"close_date": "2021-01-02", "profit_abs": 100},
              {"close_date": "2021-01-03", "profit_abs": -110}]
    r = montecarlo.trade_returns(trades, 1000.0)
    assert list(r) == pytest.approx([0.10, -0.10])


def test_simulation_is_repeatable_and_sane():
    r = np.array([0.02, -0.01] * 50)
    a = montecarlo.simulate(r, years=1.0, runs=300)
    b = montecarlo.simulate(r, years=1.0, runs=300)
    assert a == b  # fixed seed
    assert 0 < a["dd_median"] <= a["dd_p95"] <= a["dd_worst"] < 1
    assert a["cagr_p5"] <= a["cagr_median"]
    assert 0 <= a["loss_chance"] <= 1


def test_all_losing_trades_always_lose():
    a = montecarlo.simulate(np.array([-0.01] * 30), years=1.0, runs=50)
    assert a["loss_chance"] == 1.0


def test_montecarlo_command_runs_in_docker_and_never_on_test_slice():
    c = cmd("montecarlo", "--slice", "train", "--strategy", "TrendEma")
    assert "/freqtrade/scripts/montecarlo.py" in c
    with pytest.raises(SystemExit):
        cmds("montecarlo", "--slice", "test", "--strategy", "TrendEma")


def _hourly(values, start="2024-01-01"):
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="1h", tz="UTC"), dtype=float)


def test_dca_flat_price_keeps_money_without_fee():
    eq = benchmark.dca_equity({"A": _hourly([100.0] * 24 * 21)}, fee=0.0)
    assert eq.iloc[0] == pytest.approx(1.0)
    assert eq.iloc[-1] == pytest.approx(1.0)


def test_dca_spends_everything_by_the_end():
    # 3 weeks -> 3 buys; price doubles in week 3, only coins gain
    prices = [100.0] * (24 * 14) + [200.0] * (24 * 7)
    eq = benchmark.dca_equity({"A": _hourly(prices)}, fee=0.0)
    # 2/3 bought at 100 (now worth 2x), 1/3 bought at 200 (1x) -> 4/3 + 1/3
    assert eq.iloc[-1] == pytest.approx(2 * 2 / 3 + 1 / 3)


def test_dca_falls_less_than_buy_and_hold_in_an_early_crash():
    prices = [100.0] + [50.0] * (24 * 28)
    closes = {"A": _hourly(prices)}
    dca = benchmark.max_drawdown(benchmark.dca_equity(closes, fee=0.0))
    bh = benchmark.max_drawdown(benchmark.buy_and_hold_equity(closes, fee=0.0))
    assert dca < bh


def test_dca_pays_fee_on_buys_and_final_sale():
    eq = benchmark.dca_equity({"A": _hourly([100.0] * 24 * 14)}, fee=0.01)
    assert eq.iloc[-1] == pytest.approx(0.99 * 0.99)


# --- fresh (forward) slice -----------------------------------------------------


def test_fresh_starts_where_test_ends_and_never_overlaps():
    from splits import fresh_slice

    f = fresh_slice(date(2026, 11, 1))
    assert f.start == SLICES["test"].end
    assert f.end == date(2026, 11, 1)
    assert f.timerange == "20261001-20261101"
    # a clock before the data end can never produce a slice that reaches back into test
    assert fresh_slice(date(2020, 1, 1)).start == SLICES["test"].end


def test_fresh_backtest_needs_no_final_test_flag():
    c = ft.build_commands(ft.parse_args(["backtest", "--slice", "fresh"]))[0]
    assert c[c.index("--timerange") + 1] == SLICES["fresh"].timerange


def test_window_warning_only_when_buy_and_hold_starts_late():
    idx_ok = pd.date_range("2021-01-01", periods=3, freq="1h", tz="UTC")
    idx_late = pd.date_range("2022-03-17", periods=3, freq="1h", tz="UTC")
    assert benchmark.window_warning(date(2021, 1, 1), idx_ok) is None
    assert "2022-03-17" in benchmark.window_warning(date(2021, 1, 1), idx_late)


def test_early_slice_ends_where_train_starts():
    e = SLICES["early"]
    assert e.end == SLICES["train"].start
    assert e.timerange == "20180101-20210101"


def test_download_early_prepends_old_candles():
    cmds = ft.build_commands(ft.parse_args(["download", "--universe", "early", "--early"]))
    first = cmds[0]
    assert "--prepend" in first
    assert first[first.index("--timerange") + 1] == "20170801-"
    plain = ft.build_commands(ft.parse_args(["download"]))[0]
    assert "--prepend" not in plain


def test_core_gold_universe_is_core_plus_paxg():
    from universe import UNIVERSES

    assert UNIVERSES["core_gold"][:5] == ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]
    assert UNIVERSES["core_gold"][5] == "PAXG/USDT" and len(UNIVERSES["core_gold"]) == 6


def test_scan_breadth_line_and_ft_passthrough():
    pytest.importorskip("pandas")
    import scan

    df = pd.DataFrame({"pair": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT"],
                       "state": ["in trend", "below EMA200", "ENTRY NOW", "below EMA200", "above EMA200, short trend down", "below EMA200"],
                       "vs_ema200": [0.01, -0.02, 0.03, -0.01, 0.005, -0.04], "candle": [pd.Timestamp("2026-11-01 12:00", tz="UTC")] * 6})
    assert scan.breadth_line(df) == "2026-11-01,6,0.500,1,1,trend,below,entry,below,above_down"
    assert scan.CSV_HEADER == "date,n_coins,breadth,n_in_trend,n_entry_now,BTC,ETH,SOL,BNB,XRP"
    c = ft.build_commands(ft.parse_args(["scan", "--csv"]))[-1]
    assert c[-1] == "--csv"


def test_chart_turkish_render_and_tiny_prices():
    pytest.importorskip("pandas")
    import chart

    r = {"date": "2026-10-31", "close": 2255.66, "ema20": 2380.27, "vs_ema20": -0.052, "ema50": 2428.44, "vs_ema50": -0.071,
         "ema200": 2317.59, "vs_ema200": -0.027, "ret7": -0.044, "ret30": -0.167, "ret90": 0.196, "high60": 2776.19,
         "low60": 2245.54, "support": None, "resistance": 2359.68, "vol30": 0.36, "volume_ratio": 0.92}
    b = {"short_up": True, "above_trend": False, "entry_now": False, "vol1h": 0.45, "size_scale": 1.0, "candle": "x"}
    t = chart.render_tr("ETH/USDT", r, b)
    for must in ("Fiyat 50 günlük ortalamanın %7,1 altında: orta vadede zayıf.", "2.255,66$", "fiyatın altında dönülmüş bir dip yok",
                 "2.359,68$", "normalin (90 günlük ortalama) 0,9 katı", "Bot şu an almaz, çünkü saatlik grafikte fiyat 200 saatlik",
                 "Geçmişin okunması, tahmin değil, yatırım tavsiyesi değil."):
        assert must in t, must
    assert chart.px_tr(0.000005) == "0,000005" and chart.px_tr(74200) == "74.200,00"
    c = ft.build_commands(ft.parse_args(["chart", "--pair", "eth", "--tr"]))[-1]
    assert c[-2:] == ["--lang", "tr"]


def test_ft_test_and_minibot_run_in_the_test_image():
    t = ft.build_commands(ft.parse_args(["test", "tests/test_minibot.py"]))
    assert len(t) == 1 and t[0][-4:] == ["-m", "pytest", "-q", "tests/test_minibot.py"] and ft.TEST_IMAGE in t[0]
    assert ft.build_commands(ft.parse_args(["test", "--build"]))[0][:2] == ["docker", "build"]
    m = ft.build_commands(ft.parse_args(["minibot", "--once"]))[0]
    assert m[-3:] == ["--once", "--rule", "voltarget"] and "minibot.bot" in m
    assert (ft.ROOT / "tests" / "Dockerfile").read_text().count("freqtrade:2026.10") == 1
