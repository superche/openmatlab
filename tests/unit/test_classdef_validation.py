"""O-E3 (#620): property validation, immutable, Abstract, Hidden, mustBe* validators."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]

VPT = """classdef VPt
  properties (SetAccess = immutable)
    id = 0
  end
  properties (Hidden)
    secret = 5
  end
  properties
    x (1,1) double {mustBePositive} = 1
    name char = 'a'
    v (1,:) = [1 2]
    r {mustBeInRange(r, 0, 10)} = 3
    n (1,1) double
    k (2,2) = 0
  end
  methods
    function obj = VPt(i)
      if nargin, obj.id = i; end
    end
  end
end
"""
ABS = """classdef (Abstract) AbsS
  methods (Abstract)
    r = area(obj)
  end
end
"""
SQ = """classdef Sq < AbsS
  methods
    function r = area(obj)
      r = 4;
    end
  end
end
"""
HALF = "classdef Half < AbsS\nend\n"
AM = """classdef AM
  methods (Abstract)
    [a, b] = two(obj, x)
  end
end
"""


@pytest.fixture
def run(tmp_path):
    for n, t in {"VPt": VPT, "AbsS": ABS, "Sq": SQ, "Half": HALF, "AM": AM}.items():
        (tmp_path / f"{n}.m").write_text(t)
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line(f"addpath('{tmp_path.as_posix()}');")

    def go(code):
        r.run_line(code)
        return s.workspace.get

    return go


def _err(run, code):
    g = run(f"try, {code}; m = ''; i = ''; catch e, m = e.message; i = e.identifier; end")
    return g("m").text, g("i").text


def _n(v):
    return np.asarray(v.backend_buffer()).tolist()


def test_validator_rejects_and_class_converts(run):
    m, i = _err(run, "p = VPt; p.x = -1")
    assert m == "Error setting property 'x' of class 'VPt'. Value must be positive."
    assert i == "MATLAB:validators:mustBePositive"
    g = run("p = VPt; p.x = '7'; a = p.x; c = class(p.x); p.name = 65; b = p.name;")
    assert _n(g("a")) == [[55.0]] and g("c").text == "double" and g("b").text == "A"


def test_size_validation_reshape_expand_and_error(run):
    g = run("p = VPt; p.v = [1; 2; 3]; s = size(p.v); p.k = 7; t = p.k;")
    assert _n(g("s")) == [[1, 3]] and _n(g("t")) == [[7, 7], [7, 7]]
    m, i = _err(run, "p = VPt; p.x = [1 2]")
    assert m.endswith("Value must be 1-by-1.") and i == "MATLAB:validation:IncompatibleSize"
    m, _ = _err(run, "p = VPt; p.v = ones(2)")
    assert m.endswith("Value must be 1-by-:.")


def test_validator_with_args_and_implicit_default(run):
    m, i = _err(run, "p = VPt; p.r = 11")
    assert "less than or equal to 10" in m and i == "MATLAB:validators:mustBeInRange"
    g = run("p = VPt; n = p.n; c = class(p.n);")
    assert _n(g("n")) == [[0.0]] and g("c").text == "double"


def test_immutable_set_in_constructor_only(run):
    g = run("p = VPt(3); a = p.id;")
    assert _n(g("a")) == [[3.0]]
    m, _ = _err(run, "p = VPt(3); p.id = 4")
    assert "immutable" in m


def test_hidden_not_displayed_but_readable(run):
    g = run("p = VPt; t = evalc('disp(p)'); h = p.secret;")
    assert "secret" not in g("t").text and _n(g("h")) == [[5.0]]


def test_abstract_classes(run):
    for code in ("a = AbsS", "h = Half", "z = AM"):
        _, i = _err(run, code)
        assert i == "MATLAB:class:abstract"
    g = run("q = Sq; r = area(q); b = isa(q, 'AbsS');")
    assert _n(g("r")) == [[4.0]] and _n(g("b")) == [[True]]


def test_mustbe_functions_direct(run):
    cases = {
        "mustBeInteger(1.5)": "Value must be integer.",
        "mustBeNumeric('a')": "Value must be numeric.",
        "mustBeNonempty([])": "Value must not be empty.",
        "mustBeGreaterThan(1, 2)": "Value must be greater than 2.",
        "mustBeMember('c', {'a', 'b'})": "Value must be a member of the specified set.",
        "mustBeText(3)": "Value must be a character vector, string array, or cell array of character vectors.",
        "mustBeNonzero([1 0])": "Value must not be zero.",
    }
    for code, msg in cases.items():
        assert _err(run, code)[0] == msg, code
    g = run("mustBePositive([1 2]); mustBeMember('a', {'a'}); mustBeText({'x'}); mustBeVector(1:3); ok = 1;")
    assert _n(g("ok")) == [[1.0]]
