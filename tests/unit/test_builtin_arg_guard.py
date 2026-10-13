"""#606: builtins never leak Python exceptions on bad or missing arguments."""

from __future__ import annotations

import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


@pytest.mark.parametrize("code", ["x = chol();", "x = diff;", "x = svd();", "x = cat({});", "x = conv(1, 2, 3, 4, 5);"])
def test_bad_arguments_raise_matlab_errors(code):
    with pytest.raises(EvalError):
        ReplSession(Session.create_default()).run_line(code)


def test_zero_args_is_minrhs():
    with pytest.raises(EvalError, match="Not enough input arguments") as ei:
        ReplSession(Session.create_default()).run_line("x = chol();")
    assert getattr(ei.value, "identifier", "") == "MATLAB:minrhs"
