"""Train / validation / test date slices. The single source of truth.

Every backtest, hyperopt and benchmark takes its dates from here, so nobody
(human or AI) can accidentally tune on the final test slice.

    train       60%  tune ideas and parameters here
    validation  20%  check that what worked in train still works
    test        20%  touched ONCE per strategy, at the very end
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


SLICES = {**compute_slices(), "fresh": fresh_slice()}
SLICE_NAMES = list(SLICES)  # for argparse choices


if __name__ == "__main__":
    for s in SLICES.values():
        print(f"{s.name:<11} {s.start} -> {s.end}   --timerange {s.timerange}")
