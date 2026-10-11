"""Expected-value helpers for M2 conformance JSON."""

from __future__ import annotations

import numpy as np
import pytest


def coerce_expected(want):
    """JSON-safe specials: string Inf/-Inf/NaN → float; nested lists recurse."""
    if isinstance(want, str):
        if want == "Inf":
            return np.inf
        if want == "-Inf":
            return -np.inf
        if want == "NaN":
            return np.nan
        raise AssertionError(f"unknown expected token {want!r}")
    if isinstance(want, list):
        return [coerce_expected(x) for x in want]
    return want


def assert_close(got: np.ndarray, want_a: np.ndarray, *, label: str) -> None:
    if want_a.shape == () or want_a.ndim == 0:
        assert got.size == 1, f"{label}: expected scalar, got {got.shape}"
        g = float(got.reshape(-1)[0])
        w = float(np.asarray(want_a).reshape(-1)[0])
        if np.isnan(w):
            assert np.isnan(g), f"{label}: expected NaN, got {g}"
        else:
            assert g == pytest.approx(w), f"{label}: {g} != {w}"
        return
    assert got.shape == want_a.shape, f"{label}: {got.shape} != {want_a.shape}"
    if np.any(np.isnan(want_a)):
        assert np.all(np.isnan(got) == np.isnan(want_a)) and np.allclose(
            np.nan_to_num(got, nan=0.0), np.nan_to_num(want_a, nan=0.0)
        ), f"{label}: {got} != {want_a}"
    else:
        assert np.allclose(got, want_a), f"{label}: {got} != {want_a}"
