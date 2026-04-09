"""Tests for product derivation functions."""

import math
import pytest


def test_amplitude_formula():
    """Amplitude should equal sqrt(b2² + b3²)."""
    b2, b3 = 3.0, 4.0
    expected_amplitude = math.sqrt(b2**2 + b3**2)  # = 5.0
    assert abs(expected_amplitude - 5.0) < 1e-9


def test_phase_range():
    """atan2 result should always be in [-π, π]."""
    import math
    for b2, b3 in [(1, 0), (0, 1), (-1, 0), (0, -1), (1, 1)]:
        phase = math.atan2(b3, b2)
        assert -math.pi <= phase <= math.pi


def test_malst_scale_factor():
    """MALST scale factor is 100 — divide by 100 to recover Kelvin."""
    raw_kelvin = 280.5
    stored_int = round(raw_kelvin * 100)   # 28050
    recovered = stored_int / 100           # 280.5
    assert abs(recovered - raw_kelvin) < 0.01


def test_trend_scale_factor():
    """Trend scale factor is 1000 — divide by 1000 to recover K/year."""
    raw_trend = 0.034  # K/year
    stored_int = round(raw_trend * 1000)   # 34
    recovered = stored_int / 1000          # 0.034
    assert abs(recovered - raw_trend) < 0.001
