"""#766: parser gaps found by the corpus (chebfun sources)."""
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.lang.parser import parse

pytestmark = pytest.mark.unit


def _out(capsys, line):
    ReplSession().run_line(line)
    return capsys.readouterr().out


def test_end_inside_matrix_subscript(capsys):
    assert _out(capsys, "x = 1:5; disp(x([1 end]))").split() == ["1", "5"]


def test_parenthesized_for_header(capsys):
    assert _out(capsys, "for (k = 1:2); disp(k); end").split() == ["1", "2"]


def test_tilde_input_and_no_paren_function():
    prog = parse("function r = f(a, ~, c)\nr = a + c;\nend\nfunction varargout = g\nvarargout = {};\nend\n")
    assert prog[0].inputs == ("a", "~", "c") and prog[1].inputs == ()


def test_anon_body_with_unary_minus_in_cell(capsys):
    assert _out(capsys, "c = {@(x) x, @(x) -x}; disp(c{2}(3))").strip() == "-3"


def test_juxtaposed_handles_in_cell(capsys):
    assert _out(capsys, "c = {@(x)sin(x) @(x)cos(2*x)}; disp(numel(c))").strip() == "2"
    assert _out(capsys, "disp([1 -2])").split() == ["1", "-2"]
