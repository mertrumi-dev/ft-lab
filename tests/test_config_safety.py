"""Safety checks for the bot config.

These tests fail if someone (human or AI) turns on real trading or puts
secrets into a file that goes to GitHub. Run them before every commit:
    python3 -m pytest
"""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "user_data" / "config"
CONFIG_FILES = sorted(CONFIG_DIR.glob("*.json"))

# Fields that must stay empty in committed config; real values live in .env.
SECRET_FIELDS = [
    ("exchange", "key"),
    ("exchange", "secret"),
    ("exchange", "password"),
    ("telegram", "token"),
    ("api_server", "jwt_secret_key"),
    ("api_server", "ws_token"),
    ("api_server", "password"),
]


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def test_config_files_exist():
    assert CONFIG_FILES, f"no config files found in {CONFIG_DIR}"


@pytest.mark.parametrize("path", CONFIG_FILES, ids=lambda p: p.name)
def test_dry_run_is_on(path):
    assert load(path).get("dry_run") is True, f"{path.name}: dry_run must be true"


@pytest.mark.parametrize("path", CONFIG_FILES, ids=lambda p: p.name)
def test_spot_only(path):
    # No leverage / futures in this project.
    assert load(path).get("trading_mode", "spot") == "spot"


@pytest.mark.parametrize("path", CONFIG_FILES, ids=lambda p: p.name)
@pytest.mark.parametrize("section,field", SECRET_FIELDS)
def test_no_secrets_in_config(path, section, field):
    value = load(path).get(section, {}).get(field, "")
    assert value == "", f"{path.name}: {section}.{field} must be empty, put it in .env"


def test_env_file_is_ignored():
    ignored = (ROOT / ".gitignore").read_text().splitlines()
    assert ".env" in ignored
