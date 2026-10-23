"""FD001 degradation metrics against fixed formulas (M14 V-E3, Epic #996).

The expected numbers are the public definitions, written out below. They are
not produced by calling the helpers.
"""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.qa.paths import repo_root
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]

DEMO = (repo_root() / "demos" / "cmapss").as_posix()


def _run(code: str):
    session = Session.create_default()
    ReplSession(session).run_line(f"addpath('{DEMO}'); " + code)
    return session


def _n(session, name) -> np.ndarray:
    return np.asarray(session.workspace.get(name).backend_buffer(), dtype=float)


def pearson(columns) -> np.ndarray:
    """Sample Pearson correlation. Covariance divides by n-1. Diagonal is 1."""
    x = np.asarray(columns, dtype=float)
    xc = x - x.mean(axis=0, keepdims=True)
    cov = (xc.T @ xc) / (x.shape[0] - 1)
    scale = np.sqrt(np.diag(cov))
    out = cov / np.outer(scale, scale)
    np.fill_diagonal(out, 1.0)
    return out


TOY = (
    "u = [2;2;2;2;1;1;1;1]; c = [1;2;3;4;1;2;3;4]; "
    "s1 = [1;1;3;5;0;0;10;10]; s2 = [0;2;4;8;1;3;5;7]; "
    "T = table(u, c, s1, s2, 'VariableNames', {'unit','cycle','s1','s2'}); "
)


def test_failure_rul_and_early_late_match_the_formula():
    # Units are interleaved on purpose: RUL stays in T's row order, while
    # groupsummary sorts units ascending.
    # Unit 1 (last four rows), W=2: s1 early (0+0)/2=0, late (10+10)/2=10.
    #   s2 early (1+3)/2=2, late (5+7)/2=6.
    # Unit 2 (first four rows): s1 early 1, late (3+5)/2=4; s2 early 1, late 6.
    # RUL on each unit is 3,2,1,0 because failure_cycle is 4.
    session = _run(
        TOY
        + "F = cmapss_failure_cycles(T); fc = F.failure_cycle'; fu = F.unit'; nc = F.n_cycles'; "
        "rul = cmapss_train_rul(T)'; "
        "[units, early_m, late_m, delta] = cmapss_early_late(T, {'s1','s2'}, 2); uu = units'; "
        "C = cmapss_sensor_corr([s1 s2]);"
    )
    assert np.array_equal(_n(session, "fu").reshape(-1), [1, 2])
    assert np.array_equal(_n(session, "fc").reshape(-1), [4, 4])
    assert np.array_equal(_n(session, "nc").reshape(-1), [4, 4])
    assert np.array_equal(_n(session, "uu").reshape(-1), [1, 2])
    assert np.array_equal(_n(session, "rul").reshape(-1), [3, 2, 1, 0, 3, 2, 1, 0])
    assert np.allclose(_n(session, "early_m"), [[0, 2], [1, 1]])
    assert np.allclose(_n(session, "late_m"), [[10, 6], [4, 6]])
    assert np.allclose(_n(session, "delta"), [[10, 4], [3, 5]])
    columns = np.array(
        [[1, 0], [1, 2], [3, 4], [5, 8], [0, 1], [0, 3], [10, 5], [10, 7]],
        dtype=float,
    )
    expected = pearson(columns)
    assert np.allclose(expected, np.corrcoef(columns, rowvar=False))
    assert np.allclose(_n(session, "C"), expected, rtol=1e-8, atol=1e-12)


def test_window_rejects_overlap_gaps_and_a_fraction():
    session = _run(
        TOY
        + "try, cmapss_early_late(T, {'s1'}, 3); id = ''; catch err, id = err.identifier; end; "
        "ug = [1;1;1;1]; cg = [1;2;3;5]; sg = [1;2;3;4]; "
        "Tg = table(ug, cg, sg, 'VariableNames', {'unit','cycle','s1'}); "
        "try, cmapss_early_late(Tg, {'s1'}, 2); idg = ''; catch err, idg = err.identifier; end; "
        "try, cmapss_early_late(T, {'s1'}, 2.5); idw = ''; catch err, idw = err.identifier; end; "
        "try, cmapss_early_late(T, {'s1'}, 0); id0 = ''; catch err, id0 = err.identifier; end;"
    )
    for name in ("id", "idg", "idw", "id0"):
        assert session.workspace.get(name).text == "OpenMATLAB:cmapss:Window"
