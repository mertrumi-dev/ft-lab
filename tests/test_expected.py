"""Tests for scripts/expected.py (block bootstrap range check)."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import expected  # noqa: E402


def test_bootstrap_shape_and_blocks_come_from_history():
    hist = np.arange(30, dtype=float) / 1000
    paths = expected.block_bootstrap(hist, days=20, runs=50, block=7, seed=1)
    assert paths.shape == (50, 20)
    assert set(np.round(paths.ravel(), 6)) <= set(np.round(hist, 6))
    # first 7 values of a path are consecutive history values (a block)
    assert np.allclose(np.diff(paths[0, :7]), 0.001)


def test_path_stats_known_values():
    total, dd = expected.path_stats(np.array([[0.10, -0.50, 0.0]]))
    assert total[0] == pytest.approx(1.1 * 0.5 - 1)
    assert dd[0] == pytest.approx(0.5)


def test_verdict_bands():
    assert "BELOW" in expected.verdict(0.01)
    assert "inside" in expected.verdict(0.5)
    assert "above" in expected.verdict(0.99)
    assert expected.percentile_of(np.array([1, 2, 3, 4]), 2.5) == pytest.approx(0.5)
