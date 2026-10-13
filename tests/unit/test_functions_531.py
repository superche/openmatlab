"""Epic #531: varargin/varargout, nargin/nargout(+chk), global/persistent, eval/feval, exist, str2func/func2str."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _run(code, tmp_path=None, files=None):
    s = Session.create_default()
    pre = ""
    if files:
        for name, src in files.items():
            (tmp_path / name).write_text(src)
        pre = f"addpath('{tmp_path}'); "
    ReplSession(s).run_line(pre + code)
    return s


def _v(s, n):
    return np.asarray(s.workspace.get(n).backend_buffer()).tolist()


def _t(s, n):
    return s.workspace.get(n).text


VAR = {
    "vin531.m": "function [n, k] = vin531(a, varargin)\nn = nargin;\nk = numel(varargin);\nend\n",
    "vout531.m": "function varargout = vout531()\nfor i = 1:nargout\n  varargout{i} = i * 10;\nend\nend\n",
    "chk531.m": "function chk531(varargin)\nnarginchk(1, 2);\nend\n",
    "noout531.m": "function y = noout531()\nend\n",
    "cnt531.m": "function k = cnt531()\npersistent n\nif isempty(n)\n  n = 0;\nend\nn = n + 1;\nk = n;\nend\n",
    "g531.m": "function g = g531()\nglobal GG\ng = GG;\nGG = GG * 2;\nend\n",
    "cellarg531.m": "function n = cellarg531(c)\nn = numel(c);\nend\n",
}


def test_varargin_counts(tmp_path):
    s = _run("[n1, k1] = vin531(1); [n3, k3] = vin531(1, 'a', {2});", tmp_path, VAR)
    assert _v(s, "n1") == [[1]] and _v(s, "k1") == [[0]] and _v(s, "n3") == [[3]] and _v(s, "k3") == [[2]]


def test_varargout_follows_nargout(tmp_path):
    s = _run("[a, b, c] = vout531();", tmp_path, VAR)
    assert (_v(s, "a"), _v(s, "b"), _v(s, "c")) == ([[10]], [[20]], [[30]])


def test_too_many_inputs_identifier(tmp_path):
    s = _run("try, cellarg531(1, 2); catch e, i = e.identifier; end", tmp_path, VAR)
    assert _t(s, "i") == "MATLAB:TooManyInputs"


def test_fewer_inputs_allowed_until_used(tmp_path):
    s = _run("try, cellarg531(); catch e, m = e.message; end", tmp_path, VAR)
    assert "c" in _t(s, "m")  # error only when the missing input is read


def test_narginchk_ids(tmp_path):
    s = _run("try, chk531(); catch e, a = e.identifier; end; try, chk531(1,2,3); catch e, b = e.identifier; end; chk531(1);", tmp_path, VAR)
    assert _t(s, "a") == "MATLAB:narginchk:notEnoughInputs" and _t(s, "b") == "MATLAB:narginchk:tooManyInputs"


def test_unassigned_output_error(tmp_path):
    s = _run("noout531(); try, y = noout531(); catch e, i = e.identifier; end", tmp_path, VAR)
    assert _t(s, "i") == "MATLAB:unassignedOutputs"


def test_persistent_counter(tmp_path):
    s = _run("a = cnt531(); b = cnt531(); c = cnt531();", tmp_path, VAR)
    assert _v(s, "c") == [[3]]


def test_global_shared_with_function(tmp_path):
    s = _run("global GG; GG = 4; g = g531(); after = GG;", tmp_path, VAR)
    assert _v(s, "g") == [[4]] and _v(s, "after") == [[8]]


def test_cell_and_struct_args_accepted(tmp_path):
    s = _run("n = cellarg531({1, 2, 3}); m = cellarg531(struct('a', {1, 2}));", tmp_path, VAR)
    assert _v(s, "n") == [[3]] and _v(s, "m") == [[2]]


def test_nargin_of_named_function(tmp_path):
    s = _run("a = nargin('vin531'); b = nargout('vin531'); c = nargin(@cellarg531);", tmp_path, VAR)
    assert _v(s, "a") == [[-2]] and _v(s, "b") == [[2]] and _v(s, "c") == [[1]]


def test_eval_value_and_catch():
    s = _run("v = eval('6 * 7'); eval('nope_fn_531(1)', 'caught = 1;'); m = lasterr;")
    assert _v(s, "v") == [[42]] and _v(s, "caught") == [[1]] and "nope_fn_531" in _t(s, "m")


def test_eval_parse_error_is_matlab_error():
    with pytest.raises(EvalError):
        _run("eval('x = (');")


def test_feval_name_and_multiple_outputs():
    s = _run("[m, i] = feval('max', [3 9 1]); p = feval(@plus, 1, 2);")
    assert _v(s, "m") == [[9]] and _v(s, "i") == [[2]] and _v(s, "p") == [[3]]


def test_str2func_func2str_roundtrip():
    s = _run("f = str2func('@(x) x.^2 + 1'); y = f(3); t = func2str(f); n = func2str(@sin);")
    assert _v(s, "y") == [[10]] and _t(s, "t") == "@(x)x.^2+1" and _t(s, "n") == "sin"


def test_func2str_keeps_spaces_in_quotes():
    s = _run("t = func2str(@() disp('a b'));")
    assert _t(s, "t") == "@()disp('a b')"


def test_str2func_unknown_errors_on_call():
    s = _run("h = str2func('nope_531'); try, h(1); catch e, i = e.identifier; end")
    assert _t(s, "i") == "MATLAB:UndefinedFunction"


def test_exist_kinds(tmp_path):
    s = _run("x = 1; a = exist('x'); b = exist('sum'); c = exist('cellarg531'); d = exist('zz_none'); e = exist('x', 'var');", tmp_path, VAR)
    assert [_v(s, k)[0][0] for k in "abcde"] == [1, 5, 2, 0, 1]


def test_operator_functions():
    s = _run("a = minus(5, [1 2]); b = power(2, [1 3]); c = eq('ab', 'ab'); d = uminus(3); e = horzcat([1], [2 3]);")
    assert _v(s, "a") == [[4, 3]] and _v(s, "b") == [[2, 8]] and _v(s, "c") == [[True, True]]
    assert _v(s, "d") == [[-3]] and _v(s, "e") == [[1, 2, 3]]


def test_persistent_outside_function_errors():
    with pytest.raises(EvalError, match="PERSISTENT"):
        _run("persistent p")


def test_nargin_at_top_level_errors():
    with pytest.raises(EvalError):
        _run("n = nargin;")
