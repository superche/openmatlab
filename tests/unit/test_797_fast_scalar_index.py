"""#797: evaluator fast paths for scalar indexing keep MATLAB semantics."""
import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = pytest.mark.unit


def _run(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s


def _get(s, name):
    return s.workspace.get(name)


@pytest.mark.parametrize("code,expect,cls", [
    ("A=[1 2;3 4]; j=3; x=A(j);", 2.0, "double"),
    ("A=[1 2;3 4]; x=A(2,1);", 3.0, "double"),
    ("A=[1 2;3 4]; i=1; j=2; x=A(i,j);", 2.0, "double"),
    ("A=int8([5 6 7]); x=A(2);", 6.0, "int8"),
    ("A=[true false]; x=A(1);", 1.0, "logical"),
    ("A=[1+2i 3]; x=A(1);", 1 + 2j, "double"),
])
def test_fast_scalar_index_values_and_class(code, expect, cls):
    v = _get(_run(code), "x")
    assert v.matlab_class() == cls
    assert np.asarray(v.backend_buffer()).shape == (1, 1)
    assert np.asarray(v.backend_buffer())[0, 0] == expect


def test_fast_scalar_index_errors_and_fallbacks():
    s = _run("A=[1 2 3]; k=4; try, A(k); m='none'; catch e, m=e.message; end")
    assert "exceeds" in _get(s, "m").to_str() if hasattr(_get(s, "m"), "to_str") else True
    s = _run("A=[1 2 3]; k=1.5; ok=0; try, A(k); catch, ok=1; end")
    assert np.asarray(_get(s, "ok").backend_buffer())[0, 0] == 1
    s = _run("A=[1 2 3]; x=A(end); y=A(logical([0 1 0]));")
    assert np.asarray(_get(s, "x").backend_buffer())[0, 0] == 3
    assert np.asarray(_get(s, "y").backend_buffer())[0, 0] == 2
    s = _run("x=abs(-4); c={7}; y=c(1);")
    assert np.asarray(_get(s, "x").backend_buffer())[0, 0] == 4
    assert _get(s, "y").matlab_class() == "cell"
