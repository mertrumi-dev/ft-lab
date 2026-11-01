import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import ft  # noqa: E402
import scan  # noqa: E402


def _hourly(closes):
    idx = pd.date_range("2025-01-01", periods=len(closes), freq="1h", tz="UTC")
    return pd.DataFrame({"date": idx, "close": closes})


def _write(tmp_path, pair, closes):
    _hourly(closes).to_feather(tmp_path / f"{pair.replace('/', '_')}-1h.feather")


def test_states_are_sorted_best_first_and_missing_coins_are_listed(tmp_path):
    n = 24 * 40
    _write(tmp_path, "UP/USDT", np.linspace(100, 200, n))     # steady rise: in trend
    _write(tmp_path, "DOWN/USDT", np.linspace(200, 100, n))   # steady fall: below EMA200
    df, skipped = scan.scan(["DOWN/USDT", "UP/USDT", "NONE/USDT"], data_dir=tmp_path)
    assert list(df["pair"]) == ["UP/USDT", "DOWN/USDT"]
    assert df.loc[0, "state"] == "in trend" and df.loc[0, "vs_ema200"] > 0
    assert df.loc[1, "state"] == "below EMA200" and df.loc[1, "ret30"] < 0
    assert skipped == ["NONE/USDT"]


def test_too_short_history_is_skipped(tmp_path):
    _write(tmp_path, "NEW/USDT", np.linspace(1, 2, 100))
    df, skipped = scan.scan(["NEW/USDT"], data_dir=tmp_path)
    assert df.empty and skipped == ["NEW/USDT"]


def test_render_marks_core_coins_and_breadth(tmp_path):
    n = 24 * 40
    _write(tmp_path, "BTC/USDT", np.linspace(100, 200, n))
    _write(tmp_path, "AAA/USDT", np.linspace(200, 100, n))
    text = scan.render(*scan.scan(["BTC/USDT", "AAA/USDT"], data_dir=tmp_path))
    assert "BTC/USDT" in text and " *" in text
    assert "market breadth: 50%" in text
    assert "Not investment advice" in text


def test_ft_scan_downloads_1h_for_the_group_then_scans():
    cmds = ft.build_commands(ft.parse_args(["scan", "--universe", "alt2023"]))
    assert "download-data" in cmds[0] and "1h" in cmds[0] and "--erase" not in cmds[0]
    assert "--pairs" in cmds[0]
    assert cmds[1][-2:] == ["--universe", "alt2023"]
    default = ft.parse_args(["scan"])
    assert default.universe == "pool"


def test_scan_download_starts_120_days_back():
    from datetime import date
    assert ft.scan_from(date(2026, 11, 1)) == "20260704"
    cmds = ft.build_commands(ft.parse_args(["scan"]))
    assert f"{ft.scan_from()}-" in cmds[0]


def test_reborn_coins_are_flagged(tmp_path):
    n = 24 * 40
    _write(tmp_path, "LUNA/USDT", np.linspace(100, 200, n))
    text = scan.render(*scan.scan(["LUNA/USDT"], data_dir=tmp_path))
    assert "LUNA/USDT" in text and " !" in text and "Terra 2.0" in text
