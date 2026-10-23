"""bwlabel, bwconncomp, and regionprops Area/Centroid/Eccentricity (Epic #1022)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _run(code: str) -> ReplSession:
    session = ReplSession()
    session.run_line(code)
    return session


def _num(session: ReplSession, name: str) -> np.ndarray:
    return np.asarray(session.session.workspace.get(name).backend_buffer())


def test_eight_connected_diagonal_is_one_object():
    session = _run(
        "BW = logical([1 0; 0 1]); "
        "[L, n] = bwlabel(BW); [L4, n4] = bwlabel(BW, 4); "
        "CC = bwconncomp(BW); ncc = CC.NumObjects; "
        "st = regionprops(L, 'Area', 'Centroid', 'Eccentricity'); "
        "a = st.Area; c = st.Centroid; e = st.Eccentricity;"
    )
    assert _num(session, "n") == 1
    assert _num(session, "n4") == 2
    assert _num(session, "ncc") == 1
    assert _num(session, "L").tolist() == [[1.0, 0.0], [0.0, 1.0]]
    assert _num(session, "L4").tolist() == [[1.0, 0.0], [0.0, 2.0]]
    assert _num(session, "a") == 2
    assert _num(session, "c").tolist() == [[1.5, 1.5]]
    assert _num(session, "e") == pytest.approx(1.0)


def test_column_major_labels_and_moments():
    session = _run(
        "T = logical([1 0; 1 0; 0 1]); "
        "[L, n] = bwlabel(T, 4); "
        "st = regionprops(L, 'Area', 'Centroid', 'Eccentricity'); "
        "areas = [st.Area]; cx = st(1).Centroid(1); cy = st(1).Centroid(2); e = st(1).Eccentricity; "
        "S = true(2); sq = regionprops(bwlabel(S), 'Centroid', 'Eccentricity'); "
        "sc = sq.Centroid; se = sq.Eccentricity;"
    )
    assert _num(session, "n") == 2
    assert _num(session, "L").tolist() == [[1.0, 0.0], [1.0, 0.0], [0.0, 2.0]]
    assert _num(session, "areas").reshape(-1).tolist() == [2.0, 1.0]
    assert _num(session, "cx") == pytest.approx(1.0)
    assert _num(session, "cy") == pytest.approx(1.5)
    assert _num(session, "e") == pytest.approx(1.0)
    assert _num(session, "sc").reshape(-1).tolist() == pytest.approx([1.5, 1.5])
    assert _num(session, "se") == pytest.approx(0.0)


def test_bwconncomp_matches_bwlabel():
    session = _run(
        "BW = logical([1 1 0 0; 0 0 0 1; 0 0 0 1]); "
        "[L, n] = bwlabel(BW); CC = bwconncomp(BW); "
        "sL = regionprops(L, 'Area', 'Eccentricity'); "
        "sC = regionprops(CC, 'Area', 'Eccentricity'); "
        "da = sum(abs([sL.Area] - [sC.Area])); "
        "de = sum(abs([sL.Eccentricity] - [sC.Eccentricity])); "
        "ncc = CC.NumObjects; total = sum([sL.Area]);"
    )
    assert _num(session, "n") == 2
    assert _num(session, "ncc") == 2
    assert _num(session, "da") == 0
    assert _num(session, "de") == 0
    assert _num(session, "total") == 4


def test_empty_and_rejected_inputs():
    session = _run("[L, n] = bwlabel(false(2, 3)); ncc = bwconncomp(false(2)).NumObjects;")
    assert _num(session, "n") == 0
    assert _num(session, "ncc") == 0
    assert _num(session, "L").shape == (2, 3)
    with pytest.raises(EvalError, match="2-D"):
        _run("bwlabel(true(2, 2, 2));")
    with pytest.raises(EvalError, match="connectivity"):
        _run("bwlabel(true(2), 6);")
    with pytest.raises(EvalError, match="Area, Centroid, and Eccentricity"):
        _run("regionprops(true(2), 'Perimeter');")
    with pytest.raises(EvalError, match="Too many input arguments"):
        _run("bwconncomp(true(2), 8, 1);")
