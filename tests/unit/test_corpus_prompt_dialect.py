"""C03 (#763 residual, #801/#815): bare Octave '>' prompts, multi-line bracket continuation, Scilab '$'."""
import pytest

from openmatlab.qa.corpus.preprocess import deprompt, prepare

pytestmark = pytest.mark.unit


def test_bare_octave_prompt_is_deprompted():
    code, transcript = deprompt("> x = 11\nx =  11\n")
    assert code == "x = 11\n"
    assert transcript == "x =  11"


def test_multiline_bracket_literal_continues_after_prompt():
    code, transcript = deprompt(">> m = ['AB';\n'CD']\n\nm =\n\nAB\nCD\n")
    assert code == "m = ['AB';\n'CD']\n"
    assert "AB\nCD" in transcript


def test_brackets_in_strings_do_not_continue():
    code, _ = deprompt(">> s = '[';\nans = 1\n")
    assert code == "s = '[';\n"


def test_scilab_dollar_is_dialect_and_string_dollar_is_not():
    assert "dialect:scilab-dollar" in prepare("x(3:3:$) = 'Fizz';\n").notes
    assert not any(n.startswith("dialect") for n in prepare("s = '$'; y = x(1:end);\n").notes)


def test_comparison_inside_code_is_not_a_prompt():
    code, transcript = deprompt("a = b > c;\n")
    assert (code, transcript) == ("a = b > c;\n", "")
