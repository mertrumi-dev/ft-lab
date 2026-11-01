"""The 2% research strategy must never trade outside a backtest."""

import sys
from pathlib import Path

import pytest

pytest.importorskip("freqtrade")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "user_data" / "strategies"))
import research_risk  # noqa: E402
import trend_ema  # noqa: E402


class _Dp:
    def __init__(self, mode):
        self.runmode = type("R", (), {"value": mode})()


@pytest.mark.parametrize("mode", ["dry_run", "live", None])
def test_research_strategy_refuses_outside_backtest(mode):
    s = research_risk.TrendEmaRisk2({})
    if mode:
        s.dp = _Dp(mode)
    assert s.confirm_trade_entry("BTC/USDT", "limit", 1.0, 100.0, "GTC", None, None, "long") is False


def test_live_risk_rule_unchanged():
    assert trend_ema.RISK_PER_TRADE == 0.01
    assert research_risk.RESEARCH_RISK_PER_TRADE == 2 * trend_ema.RISK_PER_TRADE


def test_live_compose_never_runs_research_strategy():
    compose = (Path(__file__).resolve().parent.parent / "docker-compose.yml").read_text()
    assert "TrendEmaRisk2" not in compose
