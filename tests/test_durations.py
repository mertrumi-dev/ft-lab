"""Tests for scripts/durations.py (trade duration buckets, fees)."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import durations  # noqa: E402
import ft  # noqa: E402


def t(h, pl, stake=100.0, amount=1.0, close_rate=100.0):
    from datetime import datetime, timedelta, timezone

    o = datetime(2030, 1, 1, tzinfo=timezone.utc)
    return {"open_date": o.isoformat(), "close_date": (o + timedelta(hours=h)).isoformat(), "profit_abs": pl,
            "stake_amount": stake, "amount": amount, "close_rate": close_rate}  # fmt: skip


def test_buckets_and_fees():
    rows = durations.table([t(2, -1.0), t(5, 2.0), t(30, -3.0), t(400, 10.0)])
    by = {r["bucket"]: r for r in rows}
    assert by["< 6 saat"]["trades"] == 2 and by["< 6 saat"]["win"] == 0.5 and by["< 6 saat"]["pl"] == pytest.approx(1.0)
    assert by["1-3 gün"]["trades"] == 1 and by["> 2 hafta"]["pl"] == 10.0 and by["6-24 saat"]["win"] is None
    assert durations.fees(t(1, 0)) == pytest.approx(100 * 0.0015 + 100 * 0.0015)
    assert by["< 6 saat"]["before_fees"] == pytest.approx(1.0 + 2 * 0.3)
    text = durations.render("X", rows)
    assert "| **Toplam** | 4 |" in text and "Komisyonsuz" in text


def test_ft_durations_is_read_only_command():
    cmd = ft.build_commands(ft.parse_args(["durations", "--slice", "train", "--no-kill-switch"]))[0]
    assert "durations.py" in " ".join(cmd) and "backtesting" not in cmd and "no_kill_switch" in " ".join(cmd)
