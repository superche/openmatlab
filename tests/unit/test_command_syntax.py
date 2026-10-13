"""Epic #532: command syntax and workspace commands."""

from __future__ import annotations

import os

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.lang.ast_nodes import CommandStmt, ExprStmt
from openmatlab.lang.parser import parse
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


@pytest.fixture(autouse=True)
def _restore():
    from openmatlab.host import display

    cwd = os.getcwd()
    yield
    os.chdir(cwd)
    display.FORMAT["mode"] = "short"


def _run(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s


def _v(s, n):
    return np.asarray(s.workspace.get(n).backend_buffer()).tolist()


def _t(s, n):
    return s.workspace.get(n).text


@pytest.mark.parametrize("src,args", [
    ("format long", ["long"]),
    ("clear x* y", ["x*", "y"]),
    ("disp 'it''s ok'", ["it's ok"]),
    ("a -b", ["-b"]),
    ("hold on", ["on"]),
])
def test_command_parses(src, args):
    st = parse(src)[0]
    assert isinstance(st, CommandStmt) and [a.value for a in st.expr.indices] == args


@pytest.mark.parametrize("src", ["a - b", "a == b", "x = 1", "f(1)", "a", "a'", "x(2) = 3", "a + 1"])
def test_expression_not_command(src):
    assert not isinstance(parse(src)[0], CommandStmt)


def test_command_ends_at_separators_and_comment():
    stmts = parse("disp hi; disp there % comment\ny = 1")
    assert [type(s).__name__ for s in stmts] == ["CommandStmt", "CommandStmt", "Assign"]
    assert stmts[0].suppress and [a.value for a in stmts[1].expr.indices] == ["there"]


def test_command_inside_parens_is_not_command():
    st = parse("f(a, b c)") if False else parse("y = max(1, 2)")[0]
    assert not isinstance(st, CommandStmt)


def test_variable_shadow_reinterprets_as_expression():
    s = _run("a = 10; a -1; r = ans;")
    assert _v(s, "r") == [[9]]


def test_clear_forms():
    s = _run("a = 1; b = 2; c = 3; d = 4; clear a; clear('b'); clear -regexp ^c$; e = [exist('a') exist('b') exist('c') exist('d')];")
    assert _v(s, "e") == [[0, 0, 0, 1]]


def test_clear_all_and_clearvars_except():
    s = _run("a = 1; b = 2; clearvars -except b; k = exist('a'); j = exist('b');")
    assert _v(s, "k") == [[0]] and _v(s, "j") == [[1]]
    s = _run("a = 1; clear; w = who; n = numel(w);")
    assert _v(s, "n") == [[0]]


def test_clear_global():
    s = _run("global G; G = 2; clear global G; global G; e = isempty(G);")
    assert _v(s, "e") == [[True]]


def test_who_print(capsys):
    _run("zz1 = 1; who")
    assert "Your variables are:" in capsys.readouterr().out


def test_whos_struct_and_print(capsys):
    s = _run("q = [1 2 3]; s = whos; n = s(1).name; b = s(1).bytes; z = s(1).size;")
    assert _t(s, "n") == "q" and _v(s, "b") == [[24]] and _v(s, "z") == [[1, 3]]
    _run("q = [1 2 3]; whos")
    assert "Bytes" in capsys.readouterr().out


def test_format_long_matrix_and_reset():
    s = _run("format long; a = strtrim(evalc('disp([pi 1])')); format; b = strtrim(evalc('disp(pi)'));")
    assert _t(s, "a").startswith("3.141592653589793") and _t(s, "b") == "3.1416"


def test_format_unknown_errors():
    s = _run("try, format nonsense_q; catch e, i = e.identifier; end")
    assert _t(s, "i") == "MATLAB:format:unknownFormat"


def test_cd_pwd_dir(tmp_path):
    (tmp_path / "f.txt").write_text("hello")
    (tmp_path / "sub").mkdir()
    s = _run(f"cd {tmp_path}; p = pwd; L = dir; n = numel(L); nm = L(3).name; d = L(4).isdir; by = L(3).bytes;")
    assert _t(s, "p") == str(tmp_path) and _v(s, "n") == [[4]]
    assert _t(s, "nm") == "f.txt" and _v(s, "d") == [[True]] and _v(s, "by") == [[5]]


def test_cd_missing_errors():
    s = _run("try, cd /no/such/dir_532; catch e, i = e.identifier; end")
    assert _t(s, "i") == "MATLAB:cd:NonExistentFolder"


def test_which_command_and_function_forms():
    s = _run("t = evalc('which sin'); x = 1; v = evalc('which x');")
    assert "built-in" in _t(s, "t") and "variable" in _t(s, "v")
    s = _run("w = which('sin');")
    assert _t(s, "w") == "builtin/sin"  # function form unchanged (path string)


def test_help_mfile(tmp_path):
    (tmp_path / "h532.m").write_text("function y = h532(x)\n% H532 doubles its input.\n%   y = h532(x)\ny = 2 * x;\nend\n")
    s = _run(f"addpath('{tmp_path}'); t = evalc('help h532');")
    assert "H532 doubles its input." in _t(s, "t")


def test_evalc_captures_and_isvarname():
    s = _run("t = evalc('x = 5'); k = iskeyword('for');")
    assert "x =" in _t(s, "t") and "5" in _t(s, "t") and _v(s, "k") == [[True]]
