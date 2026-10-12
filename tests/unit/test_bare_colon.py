"""Bare colon A(i,:) / A(:) (Issue #204)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.lang.ast_nodes import ColonExpr, IndexExpr
from openmatlab.lang.parser import parse
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _run(code: str, name: str):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return np.asarray(s.workspace.get(name).backend_buffer())


def test_parse_bare_colon():
    ix = parse("A(:,1)")[0].expr
    assert isinstance(ix, IndexExpr)
    assert isinstance(ix.indices[0], ColonExpr)
    assert ix.indices[0].start is None and ix.indices[0].stop is None


def test_row_col_linear_read():
    assert _run("A = [1 2 3; 4 5 6]; B = A(1,:);", "B").tolist() == [[1, 2, 3]]
    assert _run("A = [1 2 3; 4 5 6]; B = A(:,2);", "B").tolist() == [[2], [5]]
    assert list(_run("A = [1 2; 3 4]; B = A(:);", "B").reshape(-1)) == [1, 3, 2, 4]


def test_assign_row():
    B = _run("A = zeros(2,3); A(1,:) = [1 2 3]; B = A;", "B")
    assert B.tolist() == [[1, 2, 3], [0, 0, 0]]


def test_c02_conformance_script():
    s = Session.create_default()
    ReplSession(s).run_line('run("tests/conformance/scripts/c02_indexing.m");')
    A = np.asarray(s.workspace.get("A").backend_buffer())
    assert A.tolist() == [[7, 2, 3], [8, 0, 9]]


@pytest.mark.parametrize(
    "src, shape",
    [
        ("A = [1 2; 3 4];", (4, 1)),
        ("A = [1 2 3];", (3, 1)),  # row source still yields a column
        ("A = [1; 2; 3];", (3, 1)),
        ("A = 7;", (1, 1)),
        ("A = zeros(0, 3);", (0, 1)),
        ("A = zeros(1, 0);", (0, 1)),
    ],
)
def test_colon_linear_is_always_column(src, shape):
    """Issue #208: A(:) is numel(A)×1 regardless of A's orientation/emptiness."""
    assert _run(src + " B = A(:);", "B").shape == shape
