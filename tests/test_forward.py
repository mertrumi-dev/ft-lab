"""The forward-test bot is a second dry-run, never real money, never started by default."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPOSE = (ROOT / "docker-compose.yml").read_text()


def service_block(name: str) -> str:
    m = re.search(rf"\n  {name}:\n(.*?)(?=\n  \S|\Z)", COMPOSE, re.S)
    assert m, f"service {name} missing"
    return m.group(1)


def test_forward_service_is_opt_in_and_local_only():
    block = service_block("forward-adx20")
    assert 'profiles: ["forward"]' in block  # plain `docker compose up -d` does not start it
    assert '"127.0.0.1:8081:8080"' in block
    assert "--strategy TrendEmaVolTargetAdx\n" in block + "\n"  # the exact T108 class
    assert "tradesv3.adx20.dryrun.sqlite" in block  # own database, never the main bot's
    assert "--config /freqtrade/user_data/config/forward-adx20.json" in block
    assert "forward-pyramidbtc" not in COMPOSE  # replaced (PyramidBtc failed its final test)


def test_forward_and_main_never_share_db_port_or_container():
    main, fwd = service_block("freqtrade"), service_block("forward-adx20")
    db = lambda b: re.search(r"--db-url (\S+)", b).group(1)  # noqa: E731
    port = lambda b: re.search(r'"127\.0\.0\.1:(\d+):8080"', b).group(1)  # noqa: E731
    name = lambda b: re.search(r"container_name: (\S+)", b).group(1)  # noqa: E731
    assert db(main) != db(fwd) and port(main) != port(fwd) and name(main) != name(fwd)
    assert "profiles" not in main  # the main bot stays the only default service


def test_forward_config_is_dry_run_without_secrets():
    cfg = json.loads((ROOT / "user_data" / "config" / "forward-adx20.json").read_text())
    assert cfg["dry_run"] is True
    assert not ({"exchange", "api_server", "telegram", "trading_mode"} & set(cfg))


def test_main_bot_runs_voltarget_on_its_own_db():
    # 2026-11-01: main dry-run bot switched TrendEma -> TrendEmaVolTarget (docs/journal.md).
    # New DB file so the old TrendEma dry-run record stays untouched.
    block = service_block("freqtrade")
    assert "--strategy TrendEmaVolTarget\n" in block + "\n" and "profiles" not in block
    assert "tradesv3.voltarget.dryrun.sqlite" in block
