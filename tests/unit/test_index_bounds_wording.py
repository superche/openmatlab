"""MATLAB out-of-bounds index wording (Issue #446)."""

import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _run(code):
    ReplSession(Session.create_default()).run_line(code)


def test_subscript_position_message():
    with pytest.raises(EvalError, match=r"Index in position 3 exceeds array bounds \(must not exceed 2\)\."):
        _run("A = ones(2,2,2); x = A(1,1,3);")
    with pytest.raises(EvalError, match=r"Index in position 1 exceeds array bounds \(must not exceed 2\)\."):
        _run("A = ones(2,3); x = A(3,1);")


def test_linear_message():
    with pytest.raises(EvalError, match=r"Index exceeds the number of array elements\. Index must not exceed 4\."):
        _run("v = 1:4; x = v(5);")
