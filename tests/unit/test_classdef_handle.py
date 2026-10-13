"""Handle classes and inheritance (Epic #619, M8 O02/O03)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]

FILES = {
    "Node": """classdef Node < handle
  properties
    val = 0
    next = []
  end
  methods
    function obj = Node(v)
      if nargin > 0
        obj.val = v;
      end
    end
  end
end
""",
    "Base": """classdef Base
  properties
    log = ''
  end
  methods
    function obj = Base()
      obj.log = [obj.log 'B'];
    end
    function s = who(obj)
      s = ['base:' kind(obj)];
    end
    function k = kind(obj)
      k = 'base';
    end
  end
end
""",
    "Mid": """classdef Mid < Base
  methods
    function obj = Mid()
      obj.log = [obj.log 'M'];
    end
    function k = kind(obj)
      k = ['mid/' kind@Base(obj)];
    end
  end
end
""",
    "Leaf": """classdef Leaf < Mid
  methods
    function k = kind(obj)
      k = 'leaf';
    end
  end
end
""",
}


@pytest.fixture
def run(tmp_path):
    for name, src in FILES.items():
        (tmp_path / f"{name}.m").write_text(src)
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line(f"addpath('{tmp_path.as_posix()}');")

    def go(code):
        r.run_line(code)
        return s

    return go


def _v(s, n):
    v = s.workspace.get(n)
    if hasattr(v, "text"):
        return v.text
    return np.asarray(v.backend_buffer()).reshape(-1).tolist()


def test_handle_shared_through_struct_and_cell(run):
    s = run("a = Node(1); st.h = a; c = {a}; st.h.val = 5; c{1}.val = c{1}.val + 1; v = a.val;")
    assert _v(s, "v") == [6]


def test_linked_handles(run):
    s = run("a = Node(1); b = Node(2); a.next = b; a.next.val = 20; v = b.val; t = a.next == b;")
    assert _v(s, "v") == [20] and _v(s, "t") == [1]


def test_handle_equality_errors_on_mixed(run):
    s = run("a = Node(1); try, q = (a == 5); ok = 0; catch, ok = 1; end")
    assert _v(s, "ok") == [1]


def test_value_class_has_no_default_eq_or_isvalid(run):
    s = run("b = Base(); try, q = (b == b); e1 = 0; catch, e1 = 1; end;"
            " try, isvalid(b); e2 = 0; catch, e2 = 1; end")
    assert _v(s, "e1") == [1] and _v(s, "e2") == [1]


def test_implicit_superclass_constructor_order(run):
    s = run("m = Mid(); g = m.log; l = Leaf(); gl = l.log;")
    assert _v(s, "g") == "BM" and _v(s, "gl") == "BM"


def test_dispatch_and_super_method(run):
    s = run("w1 = who(Mid()); w2 = who(Leaf()); w3 = who(Base());")
    assert (_v(s, "w1"), _v(s, "w2"), _v(s, "w3")) == ("base:mid/base", "base:leaf", "base:base")


def test_isa_superclasses_and_deleted_handle(run):
    s = run("l = Leaf(); i = [isa(l, 'Mid') isa(l, 'Base') isa(l, 'handle')];"
            " sc = superclasses(l); n = numel(sc);"
            " h = Node(1); delete(h); try, h.val; e = 0; catch err, e = strcmp(err.identifier, 'MATLAB:class:InvalidHandle'); end")
    assert _v(s, "i") == [1, 1, 0] and _v(s, "n") == [2] and _v(s, "e") == [1]


def test_mixing_handle_and_value_superclasses_errors(tmp_path):
    (tmp_path / "V.m").write_text("classdef V\nend\n")
    (tmp_path / "H.m").write_text("classdef H < handle\nend\n")
    (tmp_path / "Mix.m").write_text("classdef Mix < V & H\nend\n")
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line(f"addpath('{tmp_path.as_posix()}');")
    r.run_line("try, Mix(); ok = 0; catch e, ok = strcmp(e.identifier, 'MATLAB:class:handleAndValue'); end")
    assert np.asarray(s.workspace.get("ok").backend_buffer()).item() == 1
