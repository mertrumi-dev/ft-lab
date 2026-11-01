"""Tests for scripts/deflated.py against the numerical example in Bailey & Lopez de Prado (2014)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import deflated  # noqa: E402


def test_norm_ppf_known_values():
    assert deflated.norm_ppf(0.5) == pytest.approx(0.0, abs=1e-9)
    assert deflated.norm_ppf(0.99) == pytest.approx(2.326348, abs=1e-5)
    assert deflated.norm_ppf(0.01) == pytest.approx(-2.326348, abs=1e-5)


def test_paper_example():
    # Paper: annual SR 2.5, T = 1250 days, skew -3, kurtosis 10, N = 100 trials,
    # variance of the trials' annual SR = 0.5 -> SR0 ~ 0.1132 (daily), DSR ~ 0.90
    var_daily = 0.5 / 250
    sr0 = deflated.expected_max_sharpe(var_daily, 100)
    assert sr0 == pytest.approx(0.1132, abs=5e-4)
    p = deflated.psr(2.5 / np.sqrt(250), sr0, 1250, -3, 10)
    assert p == pytest.approx(0.90, abs=0.01)


def test_more_trials_means_higher_bar():
    assert deflated.expected_max_sharpe(0.001, 1000) > deflated.expected_max_sharpe(0.001, 10)


def test_dsr_on_series():
    rng = np.random.default_rng(0)
    r = pd.Series(rng.normal(0.002, 0.01, 2000))
    out = deflated.dsr(r, var_sr=1e-6, n_trials=10)  # almost no trial spread -> bar near 0
    assert out["dsr"] > 0.99 and out["t"] == 2000
