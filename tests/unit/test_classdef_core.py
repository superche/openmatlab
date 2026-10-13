"""classdef core: parsing, value classes, constructors, methods, property attributes (Epic #618, M8)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.lang.classdef_parser import is_classdef_source, parse_classdef
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]

PT = """classdef Pt
  properties
    x = 0
    y (1,1) double = 2   % size/class spec accepted
  end
  methods
    function obj = Pt(x)
      if nargin > 0
        obj.x = x;
      end
    end
    function obj = bump(obj)
      obj.x = obj.x + 1;
    end
    function r = twice(obj)
      r = helper(obj.x);
    end
  end
end
function r = helper(v)
  r = 2 * v;
end
"""


def _session(tmp_path, files):
    for name, src in files.items():
        (tmp_path / f"{name}.m").write_text(src)
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line(f"addpath('{tmp_path.as_posix()}');")
    return s, r


def _val(s, name):
    return np.asarray(s.workspace.get(name).backend_buffer()).reshape(-1).tolist()


def test_parser_blocks_and_attributes():
    node = parse_classdef(PT)
    assert node.name == "Pt" and [p.name for p in node.props] == ["x", "y"]
    assert [m.defn.name for m in node.methods] == ["Pt", "bump", "twice", "helper"]
    assert node.methods[-1].attrs.get("_local")
    assert is_classdef_source("% comment\nclassdef (Sealed) A < handle\nend\n")
    n2 = parse_classdef("classdef (Sealed) A < B & C\n properties (SetAccess = private, ~Hidden)\n p\n end\nend")
    assert n2.supers == ("B", "C") and n2.attrs == {"sealed": True}
    assert n2.props[0].attrs == {"setaccess": "private", "hidden": False}


def test_value_semantics_and_local_functions(tmp_path):
    s, r = _session(tmp_path, {"Pt": PT})
    r.run_line("a = Pt(5); b = a; b.x = 9; c = bump(a); d = a.twice(); y = a.y;")
    r.run_line("ax = a.x; bx = b.x; cx = c.x;")
    assert (_val(s, "ax"), _val(s, "bx"), _val(s, "cx"), _val(s, "d"), _val(s, "y")) == ([5], [9], [6], [10], [2])


def test_default_constructor_and_errors(tmp_path):
    s, r = _session(tmp_path, {"Pt": PT})
    r.run_line("p = Pt; px = p.x;")
    assert _val(s, "px") == [0]
    r.run_line("try, Pt(1, 2); e1 = 0; catch err, e1 = strcmp(err.identifier, 'MATLAB:TooManyInputs'); end")
    r.run_line("try, p.zz = 1; e2 = 0; catch err, e2 = strcmp(err.identifier, 'MATLAB:noPublicFieldForClass'); end")
    r.run_line("try, q = p.zz; e3 = 0; catch err, e3 = strcmp(err.identifier, 'MATLAB:noSuchMethodOrField'); end")
    assert (_val(s, "e1"), _val(s, "e2"), _val(s, "e3")) == ([1], [1], [1])


def test_display_default(tmp_path, capsys):
    s, r = _session(tmp_path, {"Pt": PT})
    r.run_line("p = Pt(3)")
    out = capsys.readouterr().out
    assert "Pt with properties:" in out and "x: 3" in out and "y: 2" in out


def test_file_name_must_match(tmp_path):
    (tmp_path / "Wrong.m").write_text("classdef Other\nend\n")
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line(f"addpath('{tmp_path.as_posix()}');")
    r.run_line("try, Wrong(); ok = 0; catch e, ok = ~isempty(strfind(e.message, 'must match')); end")
    assert _val(s, "ok") == [1]


def test_property_attributes(tmp_path):
    src = """classdef Acc
  properties (Constant)
    LIMIT = 10
  end
  properties (SetAccess = private)
    n = 0
  end
  properties (Dependent)
    twice
  end
  methods
    function obj = add(obj, k)
      obj.n = min(obj.n + k, Acc.LIMIT);
    end
    function v = get.twice(obj)
      v = 2 * obj.n;
    end
  end
end
"""
    s, r = _session(tmp_path, {"Acc": src})
    r.run_line("a = Acc; a = add(a, 4); a = a.add(20); n = a.n; t = a.twice; L = Acc.LIMIT;")
    assert (_val(s, "n"), _val(s, "t"), _val(s, "L")) == ([10], [20], [10])
    r.run_line("try, a.n = 1; e1 = 0; catch err, e1 = strcmp(err.identifier, 'MATLAB:class:SetProhibited'); end")
    r.run_line("try, a.twice = 1; e2 = 0; catch err, e2 = strcmp(err.identifier, 'MATLAB:class:noSetMethod'); end")
    assert (_val(s, "e1"), _val(s, "e2")) == ([1], [1])


def test_line_continuation_and_trailing_comma():
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line("x = [1, 2, ... comment\n 3]; c = {'a', ...\n 'b', ...\n}; n = numel(c);")
    assert _val(s, "x") == [1, 2, 3] and _val(s, "n") == [2]
