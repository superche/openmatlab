import pytest

from openmatlab.evaluator import EvalError, format_number, run


def test_arithmetic():
    result, _ = run("1 + 2 * 3")
    assert result == 7.0


def test_parens_and_div():
    result, _ = run("(10 - 4) / 2")
    assert result == 3.0


def test_assignment_and_use():
    result, env = run("a = 5; b = a * 2; b")
    assert env["a"] == 5.0
    assert env["b"] == 10.0
    assert result == 10.0


def test_unary():
    result, _ = run("-3 + +1")
    assert result == -2.0


def test_multi_line():
    source = """
    x = 10
    y = 20
    x + y
    """
    result, env = run(source)
    assert result == 30.0
    assert env["x"] == 10.0


def test_undefined_variable():
    with pytest.raises(EvalError, match="Undefined"):
        run("z + 1")


def test_div_by_zero():
    with pytest.raises(EvalError, match="zero"):
        run("1 / 0")


def test_format_number():
    assert format_number(3.0) == "3"
    assert "1.5" in format_number(1.5)
