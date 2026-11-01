"""Tests for deploy/preflight.py (server readiness check)."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "deploy"))
import preflight  # noqa: E402


def levels(results):
    return [level for level, _ in results]


def test_config_safe_passes():
    assert levels(preflight.check_config({"dry_run": True, "exchange": {"key": ""}})) == ["PASS"] * 3


def test_config_live_or_keys_or_futures_fail():
    assert "FAIL" in levels(preflight.check_config({"dry_run": False}))
    assert "FAIL" in levels(preflight.check_config({"dry_run": True, "trading_mode": "futures"}))
    assert "FAIL" in levels(preflight.check_config({"dry_run": True, "exchange": {"secret": "x"}}))


MAIN = 'services:\n  freqtrade:\n    image: x\n    ports:\n      - "127.0.0.1:8080:8080"\n'


def test_compose_port_must_be_localhost():
    bad = 'services:\n  freqtrade:\n    ports:\n      - "8080:8080"\n'
    assert levels(preflight.check_compose(MAIN)) == ["PASS"]
    assert levels(preflight.check_compose(bad)) == ["FAIL"]


def test_extra_bot_must_be_profile_gated_and_local():
    gated = MAIN + '\n  fwd:\n    profiles: ["forward"]\n    ports:\n      - "127.0.0.1:8081:8080"\n'
    ungated = MAIN + '\n  fwd:\n    ports:\n      - "127.0.0.1:8081:8080"\n'
    exposed = MAIN + '\n  fwd:\n    profiles: ["forward"]\n    ports:\n      - "0.0.0.0:8081:8080"\n'
    assert "FAIL" not in levels(preflight.check_compose(gated))
    assert "FAIL" in levels(preflight.check_compose(ungated))
    assert "FAIL" in levels(preflight.check_compose(exposed))


def test_real_compose_has_main_and_gated_forward():
    services = preflight.compose_services((ROOT / "docker-compose.yml").read_text())
    assert services["freqtrade"]["profiles"] is False
    others = {k: v for k, v in services.items() if k != "freqtrade"}
    assert others and all(v["profiles"] for v in others.values())
    assert all(p.startswith("127.0.0.1:") for v in services.values() for p in v["ports"])


def test_every_config_layer_must_be_dry_run(tmp_path):
    (tmp_path / "a.json").write_text('{"dry_run": true}')
    assert levels(preflight.check_all_configs(tmp_path)) == ["PASS"]
    (tmp_path / "b.json").write_text('{"dry_run": false}')
    assert levels(preflight.check_all_configs(tmp_path)) == ["FAIL"]


def test_real_compose_and_config_pass():
    import json

    assert "FAIL" not in levels(preflight.check_compose((ROOT / "docker-compose.yml").read_text()))
    config = json.loads((ROOT / "user_data" / "config" / "config.json").read_text())
    assert "FAIL" not in levels(preflight.check_config(config))


def test_env_checks_mode_without_reading(tmp_path):
    env = tmp_path / ".env"
    assert levels(preflight.check_env(env, ".env\n")) == ["FAIL"]  # missing
    env.write_text("SECRET=do-not-read\n")
    os.chmod(env, 0o644)
    assert levels(preflight.check_env(env, ".env\n")) == ["WARN", "PASS"]
    os.chmod(env, 0o600)
    assert levels(preflight.check_env(env, ".env\n")) == ["PASS", "PASS"]
    assert levels(preflight.check_env(env, "other\n"))[-1] == "FAIL"


def test_preflight_never_opens_env_content():
    source = (ROOT / "deploy" / "preflight.py").read_text()
    # .env is only stat()-ed, never read
    assert "ENV.read" not in source and "env.read" not in source and "open(ENV" not in source


DEMO = {"dry_run": True, "trading_mode": "spot", "exchange": {"name": "binance", "key": "", "secret": "", "demo_trading": False}}


def test_real_demo_config_is_safe_and_not_switched_yet():
    cfg = json.loads(preflight.DEMO_CONFIG.read_text())
    assert cfg["dry_run"] is True and cfg["trading_mode"] == "spot" and "margin_mode" not in cfg
    assert cfg["exchange"]["key"] == "" and cfg["exchange"]["secret"] == ""
    assert "leverage" not in json.dumps(cfg).lower().replace("never", "")
    assert set(levels(preflight.check_demo_config(cfg))) == {"PASS"}


def test_demo_config_can_never_combine_dry_run_false_with_a_real_exchange():
    live_real = {**DEMO, "dry_run": False}  # binance, demo_trading false -> real account
    assert "FAIL" in levels(preflight.check_demo_config(live_real))
    binance_demo = {**DEMO, "dry_run": False, "exchange": {**DEMO["exchange"], "demo_trading": True}}
    assert "FAIL" in levels(preflight.check_demo_config(binance_demo))  # Freqtrade 2026.10 has no Binance demo
    bybit_demo = {**DEMO, "dry_run": False, "exchange": {"name": "bybit", "key": "", "secret": "", "demo_trading": True}}
    assert set(levels(preflight.check_demo_config(bybit_demo))) == {"PASS"}


def test_demo_config_keys_and_futures_fail():
    keyed = {**DEMO, "exchange": {**DEMO["exchange"], "key": "abc"}}
    assert "FAIL" in levels(preflight.check_demo_config(keyed))
    assert "FAIL" in levels(preflight.check_demo_config({**DEMO, "trading_mode": "futures", "margin_mode": "isolated"}))


def test_minibot_demo_check_real_and_broken():
    src, ignore = preflight.MINIBOT_DEMO.read_text(), (preflight.ROOT / ".gitignore").read_text()
    assert set(levels(preflight.check_minibot_demo(src, ignore))) == {"PASS"}
    hardcoded = src.replace('env.get(KEY_ENV, "")', '"abc"')
    assert "FAIL" in levels(preflight.check_minibot_demo(hardcoded, ignore))
    no_guard = src.replace("assert_demo_urls(exchange)", "pass")
    assert "FAIL" in levels(preflight.check_minibot_demo(no_guard, ignore))
    assert "FAIL" in levels(preflight.check_minibot_demo(src, ignore.replace("minibot/state.demo.json", "")))


def test_state_dbs_from_compose(tmp_path):
    compose = "--db-url sqlite:////freqtrade/user_data/a.sqlite\n--db-url sqlite:////freqtrade/user_data/b.sqlite\n"
    (tmp_path / "user_data").mkdir()
    (tmp_path / "user_data" / "a.sqlite").write_bytes(b"x" * 2048)
    out = preflight.check_state_dbs(compose, tmp_path)
    assert levels(out) == ["PASS", "WARN"] and "NEW empty" in out[1][1]


def test_real_compose_dbs_are_found():
    out = preflight.check_state_dbs((ROOT / "docker-compose.yml").read_text(), Path("/nonexistent"))
    assert [m.split()[0] for _, m in out] == ["user_data/tradesv3.voltarget.dryrun.sqlite", "user_data/tradesv3.adx20.dryrun.sqlite"]


def test_clock_offset_levels():
    assert levels(preflight.check_clock(0.3)) == ["PASS"]
    assert levels(preflight.check_clock(-2.5)) == ["WARN"]
    assert levels(preflight.check_clock(None)) == ["WARN"]


def test_log_rotation():
    assert levels(preflight.check_log_rotation("local", "")) == ["PASS"]
    assert levels(preflight.check_log_rotation("json-file", '{"log-opts": {"max-size": "20m"}}')) == ["PASS"]
    assert levels(preflight.check_log_rotation("json-file", "")) == ["WARN"]
    assert levels(preflight.check_log_rotation(None, "")) == ["WARN"]
