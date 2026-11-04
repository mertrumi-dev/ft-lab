"""Train / validation / test date slices. The single source of truth.

Every backtest, hyperopt and benchmark takes its dates from here, so nobody
(human or AI) can accidentally tune on the final test slice.

    train       60%  tune ideas and parameters here
    validation  20%  check that what worked in train still works
    test        20%  touched ONCE per strategy, at the very end
    early            2018-01-01 .. 2021-01-01, BEFORE train: the 2018 crash and
                     the 2019-2020 recovery. Never used for any rule. Like fresh,
                     it only judges rules that are already fixed.
    fresh            everything AFTER the test slice, up to today (UTC). Prices
                     nobody had when the rules were made: the honest forward
                     check. It grows by itself as new candles are downloaded.
"""

from dataclasses import dataclass
from datetime import date, datetime, timezone

DATA_START = date(2021, 1, 1)  # all 5 pairs have Binance data from here
DATA_END = date(2026, 10, 1)  # fixed, so the slices never move
RATIOS = {"train": 0.6, "validation": 0.2, "test": 0.2}


@dataclass(frozen=True)
class Slice:
    name: str
    start: date
    end: date

    @property
    def timerange(self) -> str:
        """Freqtrade --timerange format: YYYYMMDD-YYYYMMDD (end exclusive)."""
        return f"{self.start:%Y%m%d}-{self.end:%Y%m%d}"


def compute_slices(start: date = DATA_START, end: date = DATA_END) -> dict[str, Slice]:
    total_days = (end - start).days
    train_end = date.fromordinal(start.toordinal() + round(total_days * RATIOS["train"]))
    val_end = date.fromordinal(
        start.toordinal() + round(total_days * (RATIOS["train"] + RATIOS["validation"]))
    )
    return {
        "train": Slice("train", start, train_end),
        "validation": Slice("validation", train_end, val_end),
        "test": Slice("test", val_end, end),
    }


def fresh_slice(today: date | None = None) -> Slice:
    """Forward data: from the end of the test slice to today (UTC), end exclusive."""
    today = today or datetime.now(timezone.utc).date()
    return Slice("fresh", DATA_END, max(today, DATA_END))


EARLY_START = date(2018, 1, 1)  # Binance USDT pairs of the big coins exist from late 2017 / 2018


def early_slice() -> Slice:
    """History before the train slice: never looked at while making any rule."""
    return Slice("early", EARLY_START, DATA_START)


# window24: 2024-01-01..2025-08-07 (start of 2024 to the end of validation). These dates were
# already used for our old coin groups, so this slice is allowed ONLY with the never-used
# "alt2024b" coins (ft.py refuses anything else). It never touches the test period.
WINDOW24 = Slice("window24", date(2024, 1, 1), date(2025, 8, 7))
WINDOW24_UNIVERSES = ("alt2024b",)

# Reserved judges (scripts/universe.py JUDGE_OLD / JUDGE_2025A): one look per pre-registered
# trial, logged. Each slice is allowed ONLY with its own judge universe and ends before the test slice.
JUDGE21 = Slice("judge21", date(2021, 1, 1), date(2025, 8, 7))
JUDGE25 = Slice("judge25", date(2025, 1, 1), date(2025, 8, 7))
# T154: funding rates only exist from 2019-09, so that trial judges early on this part of it.
EARLY19 = Slice("early19", date(2019, 9, 1), date(2021, 1, 1))
RESTRICTED_SLICES = {"window24": ("alt2024b",), "judge21": ("judge_old",), "judge25": ("judge_2025a",), "early19": ("early",)}

SLICES = {**compute_slices(), "fresh": fresh_slice(), "early": early_slice(), "window24": WINDOW24, "judge21": JUDGE21, "judge25": JUDGE25, "early19": EARLY19}
SLICE_NAMES = list(SLICES)  # for argparse choices


if __name__ == "__main__":
    for s in SLICES.values():
        print(f"{s.name:<11} {s.start} -> {s.end}   --timerange {s.timerange}")
