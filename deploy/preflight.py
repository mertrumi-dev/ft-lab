"""Pre-flight check before starting the bot on a server (or any new machine).

    python3 deploy/preflight.py

Read-only, stdlib only. Every line is PASS / WARN / FAIL; exit code 1 if any FAIL.
It never prints or reads the CONTENT of .env: it only checks that the file
exists, is not readable by other users and is gitignored.

What it checks and why:
  dry_run true, spot only, no keys   the bot can never touch real money
  every config layer dry_run true    a forward/research layer can't turn trading live
  FreqUI ports bound to 127.0.0.1    the login pages are not open to the internet
  extra bots behind a profile        a plain `docker compose up -d` starts only the main bot
  .env present, mode 600, ignored    secrets exist, only you can read them, never pushed
  docker / docker compose present    the bot runs in Docker
  disk >= 5 GB free, RAM >= 1.5 GB   candles + logs + sqlite grow over time
"""

import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "user_data" / "config" / "config.json"
COMPOSE = ROOT / "docker-compose.yml"
ENV = ROOT / ".env"
SECRET_FIELDS = [("exchange", "key"), ("exchange", "secret"), ("exchange", "password"), ("exchange", "uid")]
MIN_DISK_GB = 5
MIN_RAM_GB = 1.5


def check_all_configs(config_dir: Path) -> list[tuple[str, str]]:
    """Every config layer (main, forward, research) must keep dry_run true: a later
    --config file overrides an earlier one, so one bad layer would turn trading live."""
    bad = [p.name for p in sorted(config_dir.glob("*.json")) if json.loads(p.read_text()).get("dry_run") is not True]
    if bad:
        return [("FAIL", f"dry_run not true in: {', '.join(bad)}")]
    return [("PASS", f"dry_run true in every config layer ({len(list(config_dir.glob('*.json')))} files)")]


def check_config(config: dict) -> list[tuple[str, str]]:
    out = []
    out.append(("PASS", "dry_run is true") if config.get("dry_run") is True else ("FAIL", "dry_run is not true"))
    mode = config.get("trading_mode", "spot")
    out.append(("PASS", "spot only") if mode == "spot" else ("FAIL", f"trading_mode is {mode!r}, must be spot"))
    filled = [f"{s}.{k}" for s, k in SECRET_FIELDS if config.get(s, {}).get(k)]
    out.append(("FAIL", f"exchange keys in config.json: {', '.join(filled)}") if filled else ("PASS", "no exchange keys in config.json"))
    return out


MAIN_SERVICE = "freqtrade"  # the only service a plain `docker compose up -d` may start


def compose_services(text: str) -> dict[str, dict]:
    """Tiny parser for OUR docker-compose.yml (stdlib has no YAML): service name ->
    {"ports": [...], "profiles": bool}. Services are the 2-space-indented keys under
    `services:`; ports are the `- "a:b:c"` lines under a `ports:` key."""
    services: dict[str, dict] = {}
    current = None
    in_ports = False
    in_services = False
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("services:"):
            in_services = True
            continue
        if not in_services:
            continue
        m = re.match(r"^  ([\w.-]+):\s*$", line)
        if m:
            current, in_ports = m.group(1), False
            services[current] = {"ports": [], "profiles": False}
            continue
        if current is None:
            continue
        key = re.match(r"^    ([\w_]+):", line)
        if key:
            in_ports = key.group(1) == "ports"
            if key.group(1) == "profiles":
                services[current]["profiles"] = True
            continue
        port = re.match(r'^\s+-\s*"?([^"\s]+:\d+)"?\s*$', line)
        if in_ports and port:
            services[current]["ports"].append(port.group(1))
    return services


def check_compose(text: str) -> list[tuple[str, str]]:
    """Every published port must be bound to 127.0.0.1 (reach FreqUI through an SSH tunnel),
    and every extra bot (forward tests) must be opt-in behind a profile."""
    services = compose_services(text)
    if MAIN_SERVICE not in services:
        return [("FAIL", f"service {MAIN_SERVICE!r} not found in docker-compose.yml")]
    out = []
    for name, svc in services.items():
        open_ports = [p for p in svc["ports"] if not p.startswith("127.0.0.1:")]
        if open_ports:
            out.append(("FAIL", f"{name}: port(s) open to the network: {', '.join(open_ports)} (use 127.0.0.1:PORT:PORT)"))
        else:
            out.append(("PASS", f"{name}: ports bound to 127.0.0.1 only: {', '.join(svc['ports']) or 'none'}"))
        if name != MAIN_SERVICE and not svc["profiles"]:
            out.append(("FAIL", f"{name}: extra bot without a profile would start with a plain `docker compose up -d`"))
        elif name != MAIN_SERVICE:
            out.append(("PASS", f"{name}: opt-in (behind a profile)"))
    return out


def check_env(env: Path, gitignore: str) -> list[tuple[str, str]]:
    out = []
    if not env.exists():
        return [("FAIL", ".env missing (copy it by hand from your Mac, see deploy/README.md)")]
    mode = stat.S_IMODE(env.stat().st_mode)
    if mode & (stat.S_IRGRP | stat.S_IROTH):
        out.append(("WARN", f".env is readable by other users (mode {mode:o}); run: chmod 600 .env"))
    else:
        out.append(("PASS", f".env present, mode {mode:o}"))
    ignored = ".env" in gitignore.splitlines()
    out.append(("PASS", ".env is gitignored") if ignored else ("FAIL", ".env is NOT in .gitignore"))
    return out


def check_tools() -> list[tuple[str, str]]:
    if shutil.which("docker") is None:
        return [("FAIL", "docker not found (install Docker, see deploy/README.md)")]
    try:
        r = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        return [("FAIL", f"docker compose did not answer ({e.__class__.__name__})")]
    if r.returncode != 0:
        return [("FAIL", "docker compose plugin missing")]
    return [("PASS", r.stdout.strip())]


def ram_gb() -> float | None:
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1e9
    except (ValueError, OSError, AttributeError):
        return None


def check_resources() -> list[tuple[str, str]]:
    out = []
    free = shutil.disk_usage(ROOT).free / 1e9
    out.append(("PASS" if free >= MIN_DISK_GB else "WARN", f"disk free {free:.1f} GB (want >= {MIN_DISK_GB})"))
    ram = ram_gb()
    if ram is None:
        out.append(("WARN", "could not read RAM size"))
    else:
        out.append(("PASS" if ram >= MIN_RAM_GB else "WARN", f"RAM {ram:.1f} GB (want >= {MIN_RAM_GB})"))
    return out


def main() -> int:
    results = []
    results += check_config(json.loads(CONFIG.read_text()))
    results += check_all_configs(CONFIG.parent)
    results += check_compose(COMPOSE.read_text())
    results += check_env(ENV, (ROOT / ".gitignore").read_text())
    results += check_tools()
    results += check_resources()
    for level, message in results:
        print(f"{level:<5} {message}")
    failed = sum(level == "FAIL" for level, _ in results)
    print(f"\n{'READY' if not failed else f'NOT READY: {failed} FAIL'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
