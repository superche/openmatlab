"""O-E4 (#621): operator overloading, concatenation, subsref/subsasgn, builtin(), disp/display overloads."""

from __future__ import annotations

import io
import contextlib

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]

MONEY = """classdef Money
  properties
    c = 0
  end
  methods
    function obj = Money(c)
      if nargin, obj.c = c; end
    end
    function r = plus(a, b)
      r = Money(Money.cents(a) + Money.cents(b));
    end
    function r = uminus(a)
      r = Money(-a.c);
    end
    function r = not(a)
      r = a.c == 0;
    end
    function r = ctranspose(a)
      r = Money(a.c * 100);
    end
    function t = gt(a, b)
      t = Money.cents(a) > Money.cents(b);
    end
    function r = horzcat(varargin)
      t = 0;
      for k = 1:numel(varargin), t = t + Money.cents(varargin{k}); end
      r = Money(t);
    end
    function r = vertcat(varargin)
      r = Money(-1);
    end
    function disp(obj)
      fprintf('$%d\\n', obj.c);
    end
  end
  methods (Static)
    function x = cents(a)
      if isa(a, 'Money'), x = a.c; else, x = a; end
    end
  end
end
"""
REG = """classdef Reg < handle
  properties
    store = struct()
    hits = 0
  end
  methods
    function varargout = subsref(obj, s)
      if strcmp(s(1).type, '.')
        if strcmp(s(1).subs, 'peek')
          varargout{1} = obj.hits;
        else
          varargout{1} = builtin('subsref', obj, s);
        end
        return
      end
      obj.hits = obj.hits + 1;
      key = s(1).subs{1};
      v = obj.store.(key);
      if numel(s) > 1
        v = builtin('subsref', v, s(2:end));
      end
      varargout{1} = v;
    end
    function obj = subsasgn(obj, s, val)
      if strcmp(s(1).type, '{}')
        obj.store.(s(1).subs{1}) = val;
      else
        obj = builtin('subsasgn', obj, s, val);
      end
    end
  end
end
"""
SHOW = """classdef Shout
  methods
    function display(obj)
      fprintf('SHOUT\\n');
    end
  end
end
"""


@pytest.fixture
def run(tmp_path):
    for n, t in {"Money": MONEY, "Reg": REG, "Shout": SHOW}.items():
        (tmp_path / f"{n}.m").write_text(t)
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line(f"addpath('{tmp_path.as_posix()}');")

    def go(code):
        r.run_line(code)
        return lambda n: s.workspace.get(n)

    go.repl = r
    return go


def _n(v):
    return np.asarray(v.backend_buffer()).tolist()


def test_binary_ops_either_side_and_unary(run):
    g = run("a = Money(5); b = a + 2; c = 3 + a; d = -a; e = ~Money(0); f = a > 4; h = 1 > a; t = a'; ")
    assert [_n(g(x).get_prop("c")) for x in "bcdt"] == [[[7.0]], [[8.0]], [[-5.0]], [[500.0]]]
    assert _n(g("e")) == [[True]] and _n(g("f")) == [[True]] and _n(g("h")) == [[False]]


def test_missing_operator_errors(run):
    g = run("try, x = Money(1) * 2; m = ''; catch e, m = e.message; end")
    assert "'*'" in g("m").text


def test_concatenation_overloads(run):
    g = run("a = Money(1); h = [a 2 Money(3)]; v = [a; a]; s = [a];")
    assert _n(g("h").get_prop("c")) == [[6.0]] and _n(g("v").get_prop("c")) == [[-1.0]]
    assert _n(g("s").get_prop("c")) == [[1.0]]


def test_static_method_handle(run):
    g = run("f = @Money.cents; x = f(Money(4)); y = cellfun(@Money.cents, {Money(1), 2});")
    assert _n(g("x")) == [[4.0]] and _n(g("y")) == [[1.0, 2.0]]


def test_subsref_subsasgn_with_builtin_fallback(run):
    g = run("r = Reg; r{'a'} = [10 20 30]; x = r{'a'}; y = r{'a'}(2); n = r.peek; r.hits = 0; z = r.hits;")
    assert _n(g("x")) == [[10.0, 20.0, 30.0]] and _n(g("y")) == [[20.0]]
    assert _n(g("n")) == [[2.0]] and _n(g("z")) == [[0.0]]


def test_substruct_subsref_builtin(run):
    g = run("s.a = [1 2 3]; q = subsref(s, substruct('.', 'a', '()', {2})); t = subsasgn(s, substruct('.', 'b'), 5);"
            " b = t.b; m = builtin('max', [4 9 2]); ty = class(substruct('()', {1}));")
    assert _n(g("q")) == [[2.0]] and _n(g("b")) == [[5.0]] and _n(g("m")) == [[9.0]] and g("ty").text == "struct"


def test_disp_and_display_overloads(run):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        run.repl.run_line("a = Money(7)")
        run.repl.run_line("disp(Money(2))")
        run.repl.run_line("s = Shout")
    out = buf.getvalue()
    assert "a =" in out and "$7" in out and "$2" in out and "SHOUT" in out and "s =" not in out
