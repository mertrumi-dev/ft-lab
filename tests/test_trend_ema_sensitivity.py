import sys
from pathlib import Path

import pytest

pytest.importorskip("freqtrade")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "user_data" / "strategies"))
import trend_ema  # noqa: E402
import trend_ema_sensitivity as sens  # noqa: E402


@pytest.mark.parametrize("cls", sens.NEIGHBOURS, ids=lambda c: c.__name__)
def test_neighbour_changes_exactly_one_number_by_20_to_25_percent(cls):
    base = (trend_ema.FAST_EMA, trend_ema.SLOW_EMA, trend_ema.TREND_EMA)
    mine = (cls.fast_len, cls.slow_len, cls.trend_len)
    changed = [(b, m) for b, m in zip(base, mine) if b != m]
    assert len(changed) == 1
    b, m = changed[0]
    assert 0.2 <= abs(m - b) / b <= 0.25  # whole candles: 50 -> 40/60 is 20%
    assert cls.startup_candle_count >= 2 * cls.trend_len
    assert cls.confirm_trade_entry is trend_ema.TrendEma.confirm_trade_entry
    assert cls.stoploss == trend_ema.STOPLOSS
