"""#766: files whose functions omit `end` (MATLAB endless functions)."""
import pytest
from openmatlab.lang.parser import ParseError, parse
from openmatlab.lang.ast_nodes import FunctionDef

pytestmark = pytest.mark.unit


def test_try_end_closes_block_not_function():
    prog = parse("function r = f()\nr = 1;\ntry\n r = 2;\ncatch ME\n r = 3;\nend")
    assert len(prog) == 1 and isinstance(prog[0], FunctionDef)


def test_endless_body_stops_at_next_function():
    prog = parse("function r = f()\nr = g(1);\nfunction y = g(x)\nif x, y = 5; else, y = 0; end\n")
    assert [s.name for s in prog] == ["f", "g"]
    assert len(prog[0].body) == 1


def test_end_terminated_file_unchanged():
    prog = parse("function r = f()\nr = 1;\nend\nfunction y = g()\ny = 2;\nend\n")
    assert [s.name for s in prog] == ["f", "g"]


def test_unbalanced_end_still_errors():
    with pytest.raises(ParseError):
        parse("function r = f()\nif 1\nr = 1;\n")
