"""labeloverlay blend, palette, and Transparency (Epic #1023)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]

# First cycle color, uint8. Default transparency 0.5 on a black pixel is half of this.
_RED = (228, 26, 28)


def _run(code: str) -> ReplSession:
    session = ReplSession()
    session.run_line(code)
    return session


def _num(session: ReplSession, name: str) -> np.ndarray:
    return np.asarray(session.session.workspace.get(name).backend_buffer())


def test_default_transparency_paints_label_one_red():
    session = _run(
        "A = uint8(zeros(1, 1)); L = 1; "
        "B = labeloverlay(A, L); "
        "S = labeloverlay(A, L, 'Transparency', 0.5); "
        "Z = labeloverlay(uint8(255), 1, 'Transparency', 0); "
        "cls = class(B);"
    )
    half = tuple(int(np.rint(c / 2)) for c in _RED)
    assert _num(session, "B").reshape(-1).tolist() == list(half)
    assert _num(session, "S").reshape(-1).tolist() == list(half)
    assert _num(session, "Z").reshape(-1).tolist() == list(_RED)
    assert session.session.workspace.get("cls").text == "uint8"
    assert _num(session, "B").shape == (1, 1, 3)


def test_background_unchanged_and_label_nine_cycles():
    session = _run(
        "A = uint8(40 * ones(2)); L = [0 1; 9 2]; "
        "B = labeloverlay(A, L); "
        "T = labeloverlay(A, L, 'Transparency', 1); "
        "D = labeloverlay(double(A) / 255, L);"
    )
    raw = _num(session, "A")
    out = _num(session, "B")
    assert out.dtype == np.uint8
    assert out.shape == (2, 2, 3)
    assert np.all(out[0, 0] == raw[0, 0])
    assert np.array_equal(_num(session, "T"), np.stack([raw, raw, raw], axis=2))
    # Label 9 uses the same slot as label 1. Label 2 is the next color.
    assert np.array_equal(out[1, 0], out[0, 1])
    assert not np.array_equal(out[1, 1], out[0, 1])
    assert _num(session, "D").dtype == np.float64
    assert _num(session, "D").shape == (2, 2, 3)


def test_logical_mask_is_label_one():
    session = _run(
        "A = uint8(zeros(2)); BW = logical([1 0; 0 0]); "
        "B = labeloverlay(A, BW); "
        "one = labeloverlay(A, ones(2));"
    )
    out = _num(session, "B")
    painted = _num(session, "one")
    assert np.array_equal(out[0, 0], painted[0, 0])
    assert np.all(out[0, 1] == 0)


def test_rejected_inputs():
    with pytest.raises(EvalError, match="2-D gray or RGB"):
        _run("labeloverlay(uint8(zeros(2, 2, 2)), ones(2));")
    with pytest.raises(EvalError, match="same size"):
        _run("labeloverlay(uint8(zeros(2)), ones(3));")
    with pytest.raises(EvalError, match="nonnegative integers"):
        _run("labeloverlay(uint8(zeros(2)), -ones(2));")
    with pytest.raises(EvalError, match="between 0 and 1"):
        _run("labeloverlay(uint8(0), 1, 'Transparency', 2);")
    with pytest.raises(EvalError, match="unknown parameter"):
        _run("labeloverlay(uint8(0), 1, 'Colormap', [1 0 0]);")
    with pytest.raises(EvalError, match="Not enough input arguments"):
        _run("labeloverlay(uint8(0));")
