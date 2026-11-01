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
