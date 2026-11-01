"""Tests for scripts/health.py (read-only bot health report)."""

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import health  # noqa: E402

T0 = datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)


def stamp(minutes: int) -> str:
    return f"{T0 + timedelta(minutes=minutes):%Y-%m-%d %H:%M:%S},000"


def heartbeat(minutes: int) -> str:
    return f"{stamp(minutes)} - freqtrade.worker - INFO - Bot heartbeat. PID=1, state='RUNNING'"


WS_ERROR = [
    f"{stamp(10)} - freqtrade.exchange.exchange_ws - ERROR - Exception in continuously_async_watch_ohlcv",
    "Traceback (most recent call last):",
    '  File "x.py", line 1, in f',
    "ccxt.base.errors.NetworkError: Cannot connect to host stream.binance.com:9443",
]
MARKETS_DNS_ERROR = [
    f"{stamp(20)} - freqtrade.exchange.exchange - ERROR - Could not load markets.",
    "Traceback (most recent call last):",
    "socket.gaierror: [Errno -2] Name or service not known",
    "freqtrade.exceptions.TemporaryError: Error in reload_markets due to ExchangeNotAvailable.",
]
REAL_ERROR = [
    f"{stamp(30)} - freqtrade.strategy - ERROR - Strategy caused an error",
    "Traceback (most recent call last):",
    "KeyError: 'ema_fast'",
]


def test_network_errors_are_counted_not_failed():
    lines = [heartbeat(m) for m in range(0, 60)] + WS_ERROR + MARKETS_DNS_ERROR
    s = health.summarize_log(lines, since=T0)
    assert sum(s.network_by_hour.values()) == 2
    assert s.network_by_cause["NetworkError"] == 1
    assert s.network_by_cause["TemporaryError"] == 1  # last exception in the chain
    assert s.other_errors == []


def test_strategy_error_is_other():
    s = health.summarize_log(REAL_ERROR, since=T0)
    assert len(s.other_errors) == 1 and "Strategy caused an error" in s.other_errors[0]
    assert health.phase0_verdict(s, T0) .startswith("FAIL")


def test_errors_before_window_ignored():
    s = health.summarize_log(REAL_ERROR, since=T0 + timedelta(hours=1))
    assert s.other_errors == []


def test_heartbeat_gap_restarts_uptime():
    lines = [heartbeat(m) for m in range(0, 30)] + [heartbeat(m) for m in range(120, 150)]
    s = health.summarize_log(lines, since=T0)
    assert s.restarts == 1
    assert s.first_heartbeat == T0 + timedelta(minutes=120)


def test_phase0_verdicts():
    s = health.summarize_log([heartbeat(m) for m in range(0, 25 * 60)], since=T0)
    end = T0 + timedelta(minutes=25 * 60 - 1)
    assert health.phase0_verdict(s, end).startswith("PASS")
    assert health.phase0_verdict(s, end + timedelta(minutes=30)).startswith("FAIL")  # stale heartbeat
    short = health.summarize_log([heartbeat(m) for m in range(0, 60)], since=T0)
    assert health.phase0_verdict(short, T0 + timedelta(minutes=59)).startswith("NOT YET")
    assert health.phase0_verdict(health.LogSummary(), T0).startswith("FAIL")


def test_trade_summary_reads_db_read_only(tmp_path):
    db = tmp_path / "t.sqlite"
    con = sqlite3.connect(db)
    con.execute("create table trades (is_open boolean, close_profit_abs float, close_date datetime)")
    con.executemany(
        "insert into trades values (?, ?, ?)",
        [(0, 100.0, "2026-01-01"), (0, -250.0, "2026-01-02"), (1, None, None)],
    )
    con.commit()
    con.close()
    t = health.trade_summary(db)
    assert t["open"] == 1 and t["closed"] == 2
    # 1000 -> 1100 (peak) -> 850: drawdown 250 / 1100
    assert abs(t["drawdown"] - 250 / 1100) < 1e-9
    assert health.trade_summary(tmp_path / "missing.sqlite")["closed"] == 0


def test_drawdown_matches_strategy_formula():
    import pytest

    pytest.importorskip("freqtrade")
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "user_data" / "strategies"))
    import trend_ema

    profits = [50.0, -120.0, 30.0, -80.0]
    assert health.drawdown_from_peak(1000, profits) == trend_ema.drawdown_from_peak(1000, profits)
    assert health.KILL_SWITCH_DRAWDOWN == trend_ema.KILL_SWITCH_DRAWDOWN


def test_never_reads_env():
    source = (Path(__file__).resolve().parent.parent / "scripts" / "health.py").read_text()
    assert ".env" not in source.replace("never reads .env", "")


def test_longest_gap_is_recorded():
    lines = [heartbeat(m) for m in range(0, 30)] + [heartbeat(m) for m in range(150, 160)] + [heartbeat(m) for m in range(200, 210)]
    s = health.summarize_log(lines, since=T0)
    assert s.longest_gap == health.timedelta(minutes=121)  # 29 -> 150
    assert s.longest_gap_start == T0 + health.timedelta(minutes=29)


def test_render_with_a_gap_does_not_crash():
    lines = [heartbeat(m) for m in range(0, 30)] + [heartbeat(m) for m in range(150, 160)]
    s = health.summarize_log(lines, since=T0)
    text = health.render(s, {"open": 0, "closed": 0, "profit": 0.0, "drawdown": 0.0}, "up", T0 + health.timedelta(minutes=160), 24)
    assert "Longest gap:    2.0h" in text


def test_kill_switch_line_uses_the_worst_drawdown():
    assert abs(health.worst_drawdown(1000, [-210, 60]) - 0.21) < 1e-9
    assert abs(health.drawdown_from_peak(1000, [-210, 60]) - 0.15) < 1e-9


def test_latched_kill_switch_points_to_the_restart_checklist():
    s = health.LogSummary()
    latched = {"open": 1, "closed": 40, "profit": -150.0, "drawdown": 0.15, "worst": 0.21}
    text = health.render(s, latched, "up", T0, 24)
    assert "TRIGGERED" in text and "docs/proposals/kill-switch-restart.md" in text
    calm = {"open": 0, "closed": 3, "profit": 5.0, "drawdown": 0.01, "worst": 0.05}
    assert "kill-switch-restart" not in health.render(s, calm, "up", T0, 24)
    doc = (health.ROOT / health.RESTART_CHECKLIST).read_text()
    assert "ÖNERİ: Kaan onaylamadan" in doc and "asla düzenlenmez" in doc
