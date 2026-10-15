"""#640 residual from #569: exist class/folder, clear+global, inputname edges, inputParser switches."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _run(code, tmp_path=None, files=None):
    s = Session.create_default()
    r = ReplSession(s)
    if files:
        for k, v in files.items():
            (tmp_path / f"{k}.m").write_text(v)
        r.run_line(f"addpath('{tmp_path.as_posix()}');")
    r.run_line(code)
    return s


def _v(s, n):
    v = s.workspace.get(n)
    return v.text if hasattr(v, "text") else np.asarray(v.backend_buffer()).reshape(-1).tolist()


def test_exist_class_and_dir(tmp_path):
    s = _run("e8 = exist('Foo640'); e8c = exist('Foo640', 'class'); e2 = exist('fun640'); "
             f"e7 = exist('{tmp_path.as_posix()}', 'dir'); e0 = exist('Foo640', 'file');",
             tmp_path,
             {"Foo640": "classdef Foo640\n  properties\n    x = 1;\n  end\nend\n",
              "fun640": "function y = fun640(x)\n  y = x;\nend\n"})
    assert _v(s, "e8") == [8] and _v(s, "e8c") == [8]
    assert _v(s, "e2") == [2] and _v(s, "e7") == [7]
    # 'file' kind still reports a classdef file as present (2), matching MATLAB
    assert _v(s, "e0") == [2]


def test_clear_all_and_clearvars_global(tmp_path):
    files = {"getg": "function v = getg()\n  global g; v = g;\nend\n"}
    s = _run("global g; g = 9; clear all; global g; a = g;", tmp_path, files)
    assert _v(s, "a") == []  # empty double after clear all + redeclare
    s = _run("global g; g = 7; x = 1; clearvars -global; xe = exist('x', 'var'); "
             "global g; a = g;", tmp_path, files)
    assert _v(s, "xe") == [1] and _v(s, "a") == []
    s = _run("global g; g = 3; clear g; global g; a = g;", tmp_path, files)
    assert _v(s, "a") == [3]  # clear name unbinds local only; global value remains


def test_inputname_edges(tmp_path):
    s = _run("v = [1 2]; s = showname(v, v(1)); t = twoarg(v);", tmp_path,
             {"showname": "function s = showname(a, b)\n  s = [inputname(1) '|' inputname(2)];\nend\n",
              "twoarg": "function s = twoarg(a)\n  try, inputname(1, false); s = 'ok'; "
                        "catch e, s = e.identifier; end\nend\n"})
    assert _v(s, "s") == "v|" and _v(s, "t") == "MATLAB:TooManyInputs"


def test_inputparser_switch_partial_struct_functionname():
    s = _run("p = inputParser; addSwitch(p, 'Verbose'); parse(p, 'Verbose'); on = p.Results.Verbose;"
             " parse(p); off = p.Results.Verbose;"
             " q = inputParser; addParameter(q, 'Mode', 'fast'); q.PartialMatching = false;"
             " try, parse(q, 'Mo', 'x'); e1 = ''; catch err, e1 = err.identifier; end;"
             " r = inputParser; addParameter(r, 'Tol', 0); r.StructExpand = false; o.Tol = 1;"
             " try, parse(r, o); e2 = ''; catch err, e2 = err.identifier; end;"
             " s = inputParser; s.FunctionName = 'myfun'; addRequired(s, 'x');"
             " try, parse(s); catch err, m = err.message; i = err.identifier; end")
    assert _v(s, "on") == [True] and _v(s, "off") == [False]
    assert _v(s, "e1") == "MATLAB:InputParser:UnmatchedParameter"
    assert _v(s, "e2") == "MATLAB:InputParser:ParamMustBeChar"
    assert _v(s, "m") == "Not enough input arguments for myfun."
    assert _v(s, "i") == "MATLAB:myfun:minrhs"
