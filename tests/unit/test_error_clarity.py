"""Clear errors for incomplete ranges (#336) and misplaced `end` (#174)."""

from __future__ import annotations

import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.lang.parser import ParseError, parse
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


@pytest.mark.parametrize("src", ["y = x(1:)", "y = 1:", "y = 1:2:", "y = [1:]", "y = x(1:, 2)"])
def test_incomplete_colon_range_is_a_clear_parse_error(src):
    with pytest.raises(ParseError, match="Incomplete colon range"):
        parse(src)


def test_complete_ranges_still_parse():
    for src in ["y = x(1:end)", "y = x(:)", "y = 1:2:5", "y = x(:, 1)"]:
        parse(src)


def test_end_in_function_call_args_is_clear():
    s = Session.create_default()
    with pytest.raises(EvalError, match="end outside of an indexing expression"):
        ReplSession(s).run_line("y = sum(end);")


def test_end_in_undefined_name_reports_undefined():
    s = Session.create_default()
    with pytest.raises(EvalError, match="Undefined function or variable: foo"):
        ReplSession(s).run_line("y = foo(end);")
