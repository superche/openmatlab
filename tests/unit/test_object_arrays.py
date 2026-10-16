"""General object arrays and the indexing gaps found with them (#766)."""
import subprocess, sys
import pytest

pytestmark = pytest.mark.unit

P = "classdef P\n  properties\n    v = 0\n  end\n  methods\n    function o = P(x)\n      if nargin, o.v = x; end\n    end\n  end\nend\n"


def run(code, cwd=None):
    p = subprocess.run([sys.executable, "-m", "openmatlab", "-e", code], capture_output=True, text=True, cwd=cwd)
    return p.returncode, (p.stdout + p.stderr).rstrip()


def test_concat_index_assign_delete(tmp_path):
    (tmp_path / "P.m").write_text(P)
    rc, out = run("addpath(pwd); c = [P(1) P(2)]; disp(size(c)); disp(class(c)); c(4) = P(4); disp(numel(c)); "
                  "disp(c(3).v); c(2).v = 20; disp([c.v]); c(1) = []; disp(numel(c)); disp(size(c(2:3))); "
                  "disp(isempty(c([]))); g = [P(1); P(2)]; disp(size(g)); disp(g(end).v)", cwd=tmp_path)
    assert rc == 0 and out.split("\n") == ["   1   2", "P", "4", "0", "    1   20    0    4", "3", "   1   2", "1",
                                           "   2   1", "2"], out


def test_grow_from_empty(tmp_path):
    (tmp_path / "P.m").write_text(P)
    rc, out = run("addpath(pwd); e = []; e(2) = P(7); disp(e(2).v); disp(e(1).v); f = P(5); f(1,2) = P(6); "
                  "disp(size(f))", cwd=tmp_path)
    assert rc == 0 and out.split("\n") == ["7", "0", "   1   2"], out


def test_logical_class_kept_by_indexing():
    rc, out = run("t = [true false]; disp(class(t(1))); disp(class(t(1:2))); u = t; u(1) = false; disp(class(u)); "
                  "m = true(2); m(1,2) = 0; disp(class(m)); m(1,1) = 7; disp(class(m))")
    assert rc == 0 and out.split("\n") == ["logical", "logical", "logical", "logical", "double"], out


def test_short_logical_mask():
    rc, out = run("y = magic(3); disp(size(y(:, false))); disp(y(:, logical([1 0]))'); x = 1:3; "
                  "disp(x(logical([1 0 0 0])))")
    assert rc == 0 and out.split("\n") == ["   3   0", "   8   3   4", "1"], out


def test_empties_dropped_in_concat():
    rc, out = run("disp(size([zeros(1,0); ones(3,1)])); disp(size([zeros(0,1); zeros(1,0)]))")
    assert rc == 0 and out.split("\n") == ["   3   1", "   0   1"], out
