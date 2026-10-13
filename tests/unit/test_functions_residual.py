"""#569: multi-input cellfun, inputParser, validateattributes, inputname."""

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


def test_cellfun_multiple_inputs_and_outputs():
    s = _run("a = cellfun(@(x, y) x * y, {2, 3}, {4, 5}); [r, c] = cellfun(@size, {ones(2, 3), 1});"
             " k = cellfun(@(x, y) [x y], {1}, {2}, 'UniformOutput', false); k1 = k{1};"
             " try, cellfun(@plus, {1, 2}, {1}); e = 0; catch, e = 1; end")
    assert _v(s, "a") == [8, 15] and _v(s, "r") == [2, 1] and _v(s, "c") == [3, 1]
    assert _v(s, "k1") == [1, 2] and _v(s, "e") == [1]


def test_inputparser_flow():
    s = _run("p = inputParser; addRequired(p, 'x', @isnumeric); addOptional(p, 'n', 3, @isnumeric);"
             " addParameter(p, 'Mode', 'fast', @ischar); p.KeepUnmatched = true;"
             " parse(p, 5, 'mo', 'slow', 'Extra', 9); x = p.Results.x; n = p.Results.n; m = p.Results.Mode;"
             " ex = p.Unmatched.Extra; f = fieldnames(p.Results); f1 = f{1}; u = p.UsingDefaults; u1 = u{1};")
    assert (_v(s, "x"), _v(s, "n"), _v(s, "m"), _v(s, "ex"), _v(s, "f1"), _v(s, "u1")) == \
        ([5], [3], "slow", [9], "Mode", "n")


def test_inputparser_optional_then_struct_expand_and_errors():
    s = _run("p = inputParser; p.addOptional('n', 1); p.addParameter('Tol', 0);"
             " o.Tol = 7; p.parse(4, o); n = p.Results.n; t = p.Results.Tol;"
             " try, p.parse(1, 'Tol'); e1 = ''; catch err, e1 = err.identifier; end;"
             " q = inputParser; q.addRequired('a'); try, q.parse(); e2 = ''; catch err, e2 = err.identifier; end;"
             " try, q.addRequired('a'); e3 = ''; catch err, e3 = err.identifier; end")
    assert (_v(s, "n"), _v(s, "t")) == ([4], [7])
    assert _v(s, "e1") == "MATLAB:InputParser:ParamMissingValue"
    assert _v(s, "e2") == "MATLAB:minrhs" and _v(s, "e3") == "MATLAB:InputParser:ParamAlreadyExists"


def test_validateattributes_messages_and_ids():
    s = _run("try, validateattributes([1 2], {'numeric'}, {'scalar'}, 'myfn', 'x', 2); catch e, m = e.message; i = e.identifier; end;"
             " try, validateattributes('a', {'numeric'}, {}); catch e, t = e.identifier; end;"
             " validateattributes(magic(3), {'double'}, {'size', [3 NaN], 'positive', 'integer', '<=', 9}); ok = 1;")
    assert _v(s, "m") == "Expected input number 2, x, to be a scalar."
    assert _v(s, "i") == "MATLAB:myfn:expectedScalar"
    assert _v(s, "t") == "MATLAB:validateattributes:invalidType" and _v(s, "ok") == [1]


def test_inputname(tmp_path):
    s = _run("xx = 1; s = showname(xx, 3 + 1);", tmp_path,
             {"showname": "function s = showname(a, b)\n  s = [inputname(1) '|' inputname(2)];\nend\n"})
    assert _v(s, "s") == "xx|"
