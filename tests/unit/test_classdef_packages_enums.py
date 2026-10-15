"""O-E5 (#622): packages, import, Static methods, enumerations, introspection/metaclass."""

from __future__ import annotations

import contextlib
import io

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]

FILES = {
    "+geo/area.m": "function a = area(r)\na = pi*r^2;\nend\n",
    "+geo/+sub/twice.m": "function y = twice(x)\ny = 2*x;\nend\n",
    "+geo/Pt.m": """classdef Pt
  properties
    x = 0
  end
  methods (Static)
    function p = origin()
      p = geo.Pt();
    end
  end
  methods
    function d = norm1(obj)
      d = abs(obj.x);
    end
  end
end
""",
    "Col.m": "classdef Col\n  enumeration\n    Red, Green, Blue\n  end\nend\n",
    "Lvl.m": "classdef Lvl < int32\n  enumeration\n    Low (1)\n    High (10)\n  end\nend\n",
}


@pytest.fixture
def run(tmp_path):
    for n, t in FILES.items():
        p = tmp_path / n
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(t)
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


def test_package_functions_and_import(run):
    g = run("a = geo.area(1); b = geo.sub.twice(3); import geo.sub.twice; c = twice(4);")
    assert _n(g("b")) == [[6.0]] and _n(g("c")) == [[8.0]] and abs(_n(g("a"))[0][0] - np.pi) < 1e-12


def test_package_class_static_method(run):
    g = run("p = geo.Pt.origin(); k = class(p); m = methods('geo.Pt');")
    assert g("k").text == "geo.Pt"


def test_unresolved_package_member_is_matlab_error(run):
    g = run("try, geo.nope(1); m = ''; catch e, m = e.message; end")
    assert g("m").text == "Unable to resolve the name 'geo.nope'."


def test_enumerations_in_call_args_switch_numel(run):
    g = run("d = double(Lvl.High); c = Col.Green; switch c, case Col.Green, s = 1; otherwise, s = 0; end;"
            " [m, nm] = enumeration('Col'); n = numel(m); e = [isenum(c) isenum(3)];")
    assert _n(g("d")) == [[10.0]] and _n(g("s")) == [[1.0]] and _n(g("n")) == [[3.0]]
    assert _n(g("e")) == [[True, False]]


def test_statement_listings_print(run):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        run.repl.run_line("enumeration Col")
        run.repl.run_line("methods('geo.Pt')")
    out = buf.getvalue()
    assert "Enumeration members for class 'Col':" in out and "Methods for class geo.Pt:" in out
    assert "ans" not in out
