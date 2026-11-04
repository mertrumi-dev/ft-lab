"""Famous third-party bots are research benchmarks only: never loadable by the running bot."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import ft  # noqa: E402

THIRD = ROOT / "user_data" / "strategies" / "thirdparty"
NFI = THIRD / "NostalgiaForInfinityX8.py"


def test_nfi_has_source_and_license_header():
    head = NFI.read_text()[:2000]
    assert "github.com/iterativv/NostalgiaForInfinity" in head
    assert "GPL v3.0" in head and "RESEARCH BENCHMARK ONLY" in head
    assert (THIRD / "LICENSE-NostalgiaForInfinity").exists()


def test_bot_cannot_load_third_party_strategies():
    config = json.loads((ROOT / "user_data" / "config" / "config.json").read_text())
    assert config.get("strategy", "TrendEma") == "TrendEma"
    assert "strategy_path" not in config and "recursive_strategy_search" not in config
    assert not list((ROOT / "user_data" / "strategies").glob("NostalgiaForInfinity*.py"))
    compose = (ROOT / "docker-compose.yml").read_text()
    assert "thirdparty" not in compose and "Nostalgia" not in compose
    assert "--strategy TrendEma" in compose  # the running bot


def test_bots_config_is_dry_run_and_spot():
    cfg = json.loads((ROOT / "user_data" / "config" / "research-bots.json").read_text())
    assert cfg["dry_run"] is True
    assert "trading_mode" not in cfg and "exchange" not in cfg  # no futures, no keys


def test_nfi_backtest_gets_its_path_config_and_5m():
    (cmd,) = ft.build_commands(ft.parse_args(
        ["backtest", "--slice", "train", "--no-kill-switch", "--strategy", "NostalgiaForInfinityX8"]))
    assert cmd[cmd.index("--strategy-path") + 1] == ft.THIRD_PARTY_PATH
    assert ft.BOTS_CONFIG in cmd and cmd[cmd.index("--timeframe") + 1] == "5m"
    assert cmd[cmd.index("--fee") + 1] == "0.0015"


def test_own_strategies_do_not_get_third_party_path():
    for cmd in ft.build_commands(ft.parse_args(["backtest", "--slice", "train", "--strategy", "all"])):
        assert "--strategy-path" not in cmd


def test_fine_download_adds_5m_and_15m():
    cmds = ft.build_commands(ft.parse_args(["download", "--fine"]))
    assert any("5m" in c and "15m" in c for c in cmds)
    assert not any("5m" in c for c in ft.build_commands(ft.parse_args(["download"])))


def _closes():
    import pandas as pd

    idx = pd.date_range("2024-01-01", periods=6, freq="h", tz="UTC")
    return {"A/USDT": pd.Series([100.0, 110, 90, 95, 120, 130], index=idx), "B/USDT": pd.Series([10.0, 9, 12, 11, 10, 14], index=idx)}, idx


def _ratio(value, idx):
    import pandas as pd

    return pd.Series(value, index=idx)


def test_ratio_zero_earns_nothing_and_pays_no_fee():
    import benchmark

    closes, idx = _closes()
    for turnover in (False, True):
        assert (benchmark.exposure_matched_equity(closes, _ratio(0.0, idx), 0.0015, turnover) == 1.0).all()


def test_ratio_one_is_exactly_normal_buy_and_hold():
    import pandas as pd

    import benchmark

    closes, idx = _closes()
    normal = benchmark.buy_and_hold_equity(closes, 0.0015)
    for turnover in (False, True):
        pd.testing.assert_series_equal(benchmark.exposure_matched_equity(closes, _ratio(1.0, idx), 0.0015, turnover), normal, check_names=False)


def test_each_hour_uses_the_previous_hours_ratio_never_the_future():
    import benchmark

    closes, idx = _closes()
    a_only = {"A/USDT": closes["A/USDT"]}
    r = _ratio(0.0, idx)
    r.iloc[1] = 1.0  # invested at the END of hour 1: only hour 2 (110 -> 90) counts, not hour 1 (100 -> 110)
    eq = benchmark.exposure_matched_equity(a_only, r, 0.0)
    assert eq.iloc[1] == 1.0 and abs(eq.iloc[2] - 90 / 110) < 1e-12 and abs(eq.iloc[-1] - 90 / 110) < 1e-12


def test_half_ratio_earns_half_of_each_hour_and_rest_is_cash():
    import benchmark

    closes, idx = _closes()
    a_only = {"A/USDT": closes["A/USDT"]}
    eq = benchmark.exposure_matched_equity(a_only, _ratio(0.5, idx), 0.0)
    assert abs(eq.iloc[1] - 1.05) < 1e-12


def test_turnover_fee_costs_more_when_the_ratio_jumps_around():
    import benchmark

    closes, idx = _closes()
    jumpy = _ratio(0.0, idx)
    jumpy.iloc[::2] = 1.0
    calm = benchmark.exposure_matched_equity(closes, jumpy, 0.01).iloc[-1]
    paid = benchmark.exposure_matched_equity(closes, jumpy, 0.01, charge_turnover=True).iloc[-1]
    assert paid < calm


def test_invested_ratio_is_position_value_over_equity_and_stays_in_0_1():
    import pandas as pd

    import benchmark

    curve = pd.DataFrame({"equity": [1000.0, 1000.0, 800.0], "invested": [0.0, 250.0, 900.0]})
    assert benchmark.invested_ratio(curve).tolist() == [0.0, 0.25, 1.0]


def test_same_exposure_row_follows_the_main_bot_and_reaches_the_short_report():
    sys.path.insert(0, str(ROOT / "scripts"))
    import bots
    import kaan_report

    assert bots.matched_to(["TrendEma", "TrendEmaVolTarget"]) == "TrendEmaVolTarget"
    assert bots.matched_to(["TrendEma"]) == "TrendEma" and bots.matched_to([]) is None
    line = bots.row(bots.MATCHED_NAME, {"trades": None, "total_return": 0.1, "cagr": 0.05, "max_drawdown": 0.02, "calmar": 2.5})
    assert kaan_report.bots_rows(line)[0].startswith("Al-tut (aynı yatırım)")


def test_report_prints_the_same_exposure_block():
    sys.path.insert(0, str(ROOT / "scripts"))
    import report

    text = report.format_matched([("TrendEmaVolTarget", {"total_return": 0.1, "cagr": 0.05, "max_drawdown": 0.02, "calmar": 2.5})])
    assert "Al-tut (aynı yatırım)" in text and "TrendEmaVolTarget" in text and "2.50" in text
