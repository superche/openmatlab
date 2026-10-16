import subprocess, sys
import pytest

pytestmark = pytest.mark.unit


def run(code, cwd=None):
    p = subprocess.run([sys.executable, "-m", "openmatlab", "-e", code], capture_output=True, text=True, cwd=cwd)
    return p.returncode, (p.stdout + p.stderr).rstrip()


def test_mat2cell_blocks():
    rc, out = run("c = mat2cell(magic(4),[1 3],[2 2]); disp(size(c)); disp(c{2,1}(1,:)); d = mat2cell('abcd',1,[1 3]); disp(d{2})")
    assert rc == 0 and out.split("\n") == ["   2   2", "    5   11", "bcd"]


def test_mat2cell_bad_sizes():
    rc, out = run("mat2cell(1:3,1,[1 1])")
    assert rc != 0 and "must sum" in out and "Traceback" not in out


def test_keywords_case_sensitive(tmp_path):
    (tmp_path / "M.m").write_text("classdef M\n  properties\n    For\n    End\n  end\n  methods (Static)\n"
                                  "    function r = twice(x)\n      r = 2*x;\n    end\n  end\nend\n")
    rc, out = run("addpath(pwd); m = M; m.For = 3; disp(m.For); disp(m.twice(4))", cwd=tmp_path)
    assert rc == 0 and out.split("\n") == ["3", "8"]


@pytest.mark.parametrize("code,want", [
    ("c = {1,2,3}; d = {c{:}}; disp(size(d))", "   1   3"),
    ("c = {1,2,3}; disp([c{2:3}])", "   2   3"),
    ("c = {}; disp(max(1, c{:}))", "1"),
    ("n = {{7}}; disp(class([n{:}]))", "cell"),
    ("c = {'a';'b'}; switch 'b', case c, disp('hit'), otherwise, disp('miss'), end", "hit"),
    ("a = 1:3; a([]) = 5; disp(a)", "   1   2   3"),
    ("b = magic(3); b([], 2) = 7; disp(b(1,:))", "   8   1   6"),
])
def test_cs_lists_and_empty_subscripts(code, want):
    rc, out = run(code)
    assert rc == 0 and out == want


def test_logical_extremum_and_multi_output_handles():
    rc, out = run("a = max([true false; false false], [], 1); disp(class(a)); h = @max; [m, i] = h([3 9 2]); "
                  "disp([m i]); g = @(x) max(x); [p, q] = g([5 1 7]); disp([p q]); s.f = @size; [r, c] = s.f(ones(2,3)); disp([r c])")
    assert rc == 0 and out.split("\n") == ["logical", "   9   2", "   7   3", "   2   3"]


def test_scalar_object_paren_field_assign(tmp_path):
    (tmp_path / "R.m").write_text("classdef R\n  properties\n    L = 1\n  end\n  methods\n    function F = flip(F)\n"
                                  "      for k = 1:numel(F)\n        F(k).L = -F(k).L;\n      end\n    end\n  end\nend\n")
    rc, out = run("addpath(pwd); r = flip(R()); disp(r.L); try, r(2).L = 1; catch e, disp(e.message), end", cwd=tmp_path)
    assert rc == 0 and out.split("\n") == ["-1", "Indexed assignment is not supported for objects of class 'R' in this release."]
