"""O-E7 (#624): events/listeners, handle destructors, objects in MAT files."""

from __future__ import annotations

import contextlib
import io

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]

ACCT = """classdef Acct < handle
  properties
    bal = 0
    log = {}
  end
  events
    LowBalance
  end
  methods
    function withdraw(obj, x)
      obj.bal = obj.bal - x;
      if obj.bal < 0
        notify(obj, 'LowBalance');
      end
    end
    function delete(obj)
      fprintf('closing %d\\n', obj.bal);
    end
  end
end
"""
PT = "classdef PtM\n  properties\n    x = 1\n    y = 2\n  end\nend\n"


@pytest.fixture
def run(tmp_path):
    (tmp_path / "Acct.m").write_text(ACCT)
    (tmp_path / "PtM.m").write_text(PT)
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line(f"addpath('{tmp_path.as_posix()}'); cd('{tmp_path.as_posix()}');")

    def go(code):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            r.run_line(code)
        go.out = buf.getvalue()
        return lambda n: s.workspace.get(n)

    return go


def _n(v):
    return np.asarray(v.backend_buffer()).tolist()


def test_listener_receives_source_and_event_data(run):
    g = run("a = Acct; n = 0; lh = addlistener(a, 'LowBalance', @(s, e) fprintf('%s|%d|%s\\n', e.EventName, s.bal, class(e)));"
            " a.withdraw(3);")
    assert "LowBalance|-3|event.EventData" in run.out
    assert g("lh").matlab_class() == "event.listener"


def test_enable_disable_and_delete_listener(run):
    g = run("a = Acct; lh = addlistener(a, 'LowBalance', @(s, e) disp('hit')); lh.Enabled = false; a.withdraw(1);"
            " lh.Enabled = true; a.withdraw(1); delete(lh); a.withdraw(1); v = isvalid(lh);")
    assert run.out.count("hit") == 1 and _n(g("v")) == [[False]]


def test_method_form_and_bad_event(run):
    g = run("a = Acct; a.addlistener('LowBalance', @(s, e) disp('m')); a.notify('LowBalance');"
            " try, addlistener(a, 'Nope', @(s, e) 1); m = ''; catch err, m = err.message; end")
    assert "m" in run.out and g("m").text == "The name 'Nope' is not an accessible event for class 'Acct'."


def test_destructor_and_listener_lifetime(run):
    g = run("a = Acct; lh = listener(a, 'LowBalance', @(s, e) 1); delete(a); v = [isvalid(a) isvalid(lh)];")
    assert "closing 0" in run.out and _n(g("v")) == [[False, False]]


def test_objects_round_trip_through_mat(run):
    g = run("p = PtM; p.x = 5; a = Acct; a.bal = 7; save('objs.mat', 'p', 'a'); clear p a; load('objs.mat');"
            " c = {class(p), class(a)}; v = [p.x p.y a.bal]; s = load('objs.mat'); w = s.p.x;")
    assert _n(g("v")) == [[5.0, 2.0, 7.0]] and _n(g("w")) == [[5.0]]
    assert g("p").matlab_class() == "PtM" and g("a").matlab_class() == "Acct"
