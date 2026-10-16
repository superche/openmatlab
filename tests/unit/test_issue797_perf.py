"""#797: evaluator speed-ups keep MATLAB value semantics; double() keeps complex parts."""
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = pytest.mark.unit


def _run(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s


def _vals(s, name):
    import numpy as np
    return np.asarray(s.workspace.get(name).backend_buffer())


@pytest.mark.parametrize("alias", [
    "y = x;", "c = {x}; y = c{1};", "y = x(:)';", "w = reshape(x, 5, 1); y = w';",
    "s.a = x; y = s.a;", "h = @() x; y = h();", "y = x.';  y = y.';",
])
def test_element_store_never_leaks_into_aliases(alias):
    s = _run(f"x = zeros(1,5); {alias} x(3) = 1; x(5) = 2;")
    assert list(_vals(s, "y").reshape(-1)) == [0, 0, 0, 0, 0]
    assert list(_vals(s, "x").reshape(-1)) == [0, 0, 1, 0, 2]


def test_loop_store_in_place_matches_copy_semantics():
    s = _run("m = ones(6,1); for j = 5:-1:1, m(j) = max(j, m(j+1)); end; q = m; q(1) = -1;")
    assert list(_vals(s, "m").reshape(-1)) == [5, 5, 5, 5, 5, 1]
    assert _vals(s, "q")[0, 0] == -1


def test_scalar_read_fast_path_keeps_class_and_errors():
    s = _run("L = [true false]; a = L(2); x = int8([1 2 3]); b = x(3); z = [1+2i 3]; c = z(1);")
    assert s.workspace.get("a").matlab_class() == "logical"
    assert s.workspace.get("b").matlab_class() == "int8"
    assert complex(_vals(s, "c")[0, 0]) == 1 + 2j
    with pytest.raises(Exception, match="Index exceeds"):
        _run("x = [1 2]; y = x(3);")


def test_double_keeps_imaginary_part():
    s = _run("z = double(single(1+2i)); w = double([1i 2]);")
    assert complex(_vals(s, "z")[0, 0]) == 1 + 2j
    assert s.workspace.get("z").matlab_class() == "double"
    assert list(_vals(s, "w").reshape(-1)) == [1j, 2]


def test_nested_function_shared_workspace_store(tmp_path):
    (tmp_path / "nest797.m").write_text(
        "function r = nest797()\nx = zeros(1,3);\ninner();\nr = x;\n"
        "    function inner()\n        x(2) = 5;\n        y = x; x(3) = 1;\n    end\nend\n")
    s = _run(f"addpath('{tmp_path}'); r = nest797();")
    assert list(_vals(s, "r").reshape(-1)) == [0, 5, 1]
