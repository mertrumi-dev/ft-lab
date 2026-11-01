"""Research only: what if each trade risked 2% instead of 1%?

The live risk rule stays 1% (docs/risk-rules.md, locked by tests). This class
exists to MEASURE the trade-off in backtests: more money in coins means more
profit in rises and deeper falls. It refuses every entry outside backtest and
hyperopt, so it can never trade in dry-run or live, even if someone starts the
bot with it by mistake.
"""

from datetime import datetime

from trend_ema import MAX_STAKE_RATIO, STOPLOSS, TrendEma, risk_based_stake

RESEARCH_RISK_PER_TRADE = 0.02
RESEARCH_MAX_STAKE_RATIO = 0.50  # 2% / 8% stop = 25% of capital; cap at 50% like 2x the live cap


class TrendEmaRisk2(TrendEma):
    """TrendEma with 2% risk per trade. BACKTEST ONLY."""

    def custom_stake_amount(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_stake: float,
        min_stake: float | None,
        max_stake: float,
        leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        capital = self.wallets.get_total_stake_amount()
        stake = risk_based_stake(capital, RESEARCH_RISK_PER_TRADE, STOPLOSS, RESEARCH_MAX_STAKE_RATIO)
        return min(stake, max_stake)

    def confirm_trade_entry(self, pair: str, *args, **kwargs) -> bool:
        runmode = getattr(getattr(getattr(self, "dp", None), "runmode", None), "value", None)
        if runmode not in ("backtest", "hyperopt"):
            return False  # never trades with real or fake money
        return super().confirm_trade_entry(pair, *args, **kwargs)


assert MAX_STAKE_RATIO <= 0.25  # live cap untouched
