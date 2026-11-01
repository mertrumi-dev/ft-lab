import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "user_data" / "strategies"))
sys.path.insert(0, str(ROOT / "scripts"))

from sizing import volume_rank_flags  # noqa: E402
from universe import POOL, UNIVERSES  # noqa: E402


def _frame(volume, n=100, start="2021-01-01"):
    dates = pd.date_range(start, periods=n, freq="1h", tz="UTC")
    return pd.DataFrame({"date": dates, "close": 1.0, "volume": np.full(n, float(volume))})


def test_top_n_by_volume_and_no_lookahead():
    frames = {"A": _frame(10), "B": _frame(30), "C": _frame(20)}
    flags = volume_rank_flags(frames, top_n=2, window=5)
    assert not flags.iloc[:5].any().any()  # no full window yet (and shifted by one candle)
    last = flags.iloc[-1]
    assert last["B"] and last["C"] and not last["A"]


def test_volume_spike_counts_only_from_the_next_candle():
    a, b = _frame(10), _frame(20)
    a.loc[50, "volume"] = 10_000  # A explodes on candle 50
    flags = volume_rank_flags({"A": a, "B": b}, top_n=1, window=5)
    assert flags["B"].iloc[50]  # on candle 50 itself A's spike is not known yet
    assert flags["A"].iloc[51]


def test_pool_contains_every_group_without_duplicates():
    assert len(POOL) == len(set(POOL))
    for name in ("wide", "alt2022", "alt2023", "alt2024"):
        assert set(UNIVERSES[name]) <= set(POOL)
    assert POOL[:5] == ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]
