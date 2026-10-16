"""categorical type and methods; categorical as a table variable (Epic #692)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


@pytest.fixture
def run():
    s = Session.create_default()
    r = ReplSession(s)

    def go(code):
        r.run_line(code)
        return s

    return go


def _num(s, name):
    return np.asarray(s.workspace.get(name).backend_buffer()).reshape(-1).tolist()


def _txt(s, name):
    return s.workspace.get(name).text


def test_categories_sorted_and_counts(run):
    s = run("c = categorical({'r','g','r','b'}); k = numel(categories(c)); n = countcats(c); m = double(c);")
    assert _num(s, "k") == [3]
    assert _num(s, "n") == [1, 1, 2]
    assert _num(s, "m") == [3, 2, 3, 1]


def test_valueset_catnames_numeric(run):
    s = run("n = categorical([1 2 1 3], [1 2], {'one','two'}); a = char(n(2)); u = isundefined(n);")
    assert _txt(s, "a") == "two"
    assert _num(s, "u") == [False, False, False, True]


def test_ordinal_comparisons_and_errors(run):
    s = run("o = categorical({'lo','hi','mid'}, {'lo','mid','hi'}, 'Ordinal', true); g = o > 'lo'; "
            "c = categorical({'a'}); try, c < 'a'; e = ''; catch err, e = err.identifier; end")
    assert _num(s, "g") == [False, True, True]
    assert _txt(s, "e") == "MATLAB:categorical:NotOrdinal"


def test_add_remove_merge_rename(run):
    s = run("c = categorical({'r','g','b'}); a = numel(categories(addcats(c, {'y','z'}))); "
            "r = sum(isundefined(removecats(c, {'r','g'}))); "
            "m = categories(mergecats(c, {'g','r'}, 'x')); mm = strjoin(m', ','); "
            "q = renamecats(c, {'b','g','r'}); qq = char(q(1));")
    assert _num(s, "a") == [5]
    assert _num(s, "r") == [2]
    assert _txt(s, "mm") == "b,x"
    assert _txt(s, "qq") == "r"


def test_assignment_grows_categories_unless_protected(run):
    s = run("c = categorical({'a','b'}); c(3) = 'z'; k = numel(categories(c)); "
            "o = categorical({'a'}, {'a','b'}, 'Ordinal', true); try, o(1) = 'q'; e = ''; catch err, e = err.identifier; end")
    assert _num(s, "k") == [3]
    assert _txt(s, "e") == "MATLAB:categorical:ProtectedForAssign"


def test_index_end_colon_transpose_concat(run):
    s = run("c = categorical({'a','b','c'}); e = char(c(end)); t = size(c'); v = size(c(:)); "
            "d = [c categorical({'q'})]; k = numel(categories(d)); w = size(d);")
    assert _txt(s, "e") == "c"
    assert _num(s, "t") == [3, 1]
    assert _num(s, "v") == [3, 1]
    assert _num(s, "k") == [4]
    assert _num(s, "w") == [1, 4]


def test_display_and_undefined(run):
    s = run("c = removecats(categorical({'r','g'}), 'g'); out = evalc('c'); d = evalc('disp(c)');")
    assert "1×2 categorical array" in _txt(s, "out")
    assert "<undefined>" in _txt(s, "d")


def test_table_variable(run):
    s = run("T = table(categorical({'a';'b';'a'}), [1;2;3], 'VariableNames', {'g','x'}); "
            "k = sum(T.g == 'a'); R = T(T.g == 'b', :); v = R.x; out = evalc('T');")
    assert _num(s, "k") == [2]
    assert _num(s, "v") == [2]
    assert "a" in _txt(s, "out")


@pytest.mark.parametrize("code", [
    "categorical({1,2})", "c = categorical({'a'}); c + 1", "c = categorical({'a'}); c(5)",
    "mergecats(categorical({'a'}), {'q'})", "addcats(categorical({'a'}), 'a')", "isundefined(5)",
    "categorical([1 2], [1 1])", "categorical({'a'}, {'a'}, {'x','y'})", "countcats(5)",
])
def test_errors_are_matlab_errors(run, code):
    s = run(f"try, {code}; e = 'none'; catch err, e = err.message; end")
    msg = _txt(s, "e")
    assert msg != "none" and "internal error" not in msg and "Traceback" not in msg
