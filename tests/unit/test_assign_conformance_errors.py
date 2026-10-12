"""MATLAB assignment errors: block shape (#164), null block delete (#248), cell conversion (#292)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _run(code: str):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s


def _A(code: str):
    return np.asarray(_run(code).workspace.get("A").backend_buffer()).tolist()


def test_block_assign_requires_matching_shape():
    with pytest.raises(EvalError, match="left side is 2-by-2 and the size of the right side is 1-by-4"):
        _run("A = zeros(3); A(1:2, 1:2) = 1:4;")


def test_block_assign_allowed_forms():
    assert _A("A = zeros(2); A(1:2, 1:2) = [1 2; 3 4];") == [[1, 2], [3, 4]]
    assert _A("A = zeros(2); A(1:2, 1:2) = 7;") == [[7, 7], [7, 7]]
    # vectors match after dropping singleton dims (row into column and back)
    assert _A("A = zeros(2); A(1:2, 1) = [1 2];") == [[1, 0], [2, 0]]
    assert _A("A = zeros(2); A(1, 1:2) = [1; 2];") == [[1, 2], [0, 0]]


def test_null_assignment_block_is_error():
    with pytest.raises(EvalError, match="A null assignment can have only one non-colon index"):
        _run("A = [1 2 3; 4 5 6]; A(1, 2) = [];")
    assert _A("A = [1 2 3; 4 5 6]; A(:, 2) = [];") == [[1, 3], [4, 6]]


@pytest.mark.parametrize("rhs, cls", [("5", "double"), ("'ab'", "char"), ("true", "logical")])
def test_cell_paren_assign_non_cell_is_conversion_error(rhs, cls):
    with pytest.raises(EvalError, match=f"Conversion to cell from {cls} is not possible"):
        _run(f"c = {{1, 2}}; c(1) = {rhs};")
