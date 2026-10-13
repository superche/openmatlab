"""#529: scripts with local functions run instead of crashing; no Python traceback."""

import subprocess
import sys

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]

SCRIPT = """r = helper(3);
h = @helper;
c = cellfun(@helper, {1, 2});
z = twice_then(4);
function y = helper(x)
  y = x * 2;
end
function y = twice_then(x)
  y = helper(x) + 1;
end
"""


def _g(s, n):
    return np.asarray(s.workspace.get(n).backend_buffer())


@pytest.mark.parametrize("how", ["run", "bare"])
def test_script_local_functions(tmp_path, how):
    (tmp_path / "lfscript.m").write_text(SCRIPT)
    s = Session.create_default()
    code = f"run('{tmp_path / 'lfscript.m'}');" if how == "run" else f"addpath('{tmp_path}'); lfscript;"
    ReplSession(s).run_line(code + " k = h(5);")
    assert _g(s, "r").item() == 6 and _g(s, "c").tolist() == [[2, 4]]
    assert _g(s, "z").item() == 9 and _g(s, "k").item() == 10


def test_local_function_not_visible_after_script(tmp_path):
    (tmp_path / "lfscript.m").write_text(SCRIPT)
    s = Session.create_default()
    ReplSession(s).run_line(f"run('{tmp_path / 'lfscript.m'}');")
    with pytest.raises(EvalError):
        ReplSession(s).run_line("q = helper(1);")


def test_malformed_file_is_matlab_error_not_traceback(tmp_path):
    (tmp_path / "badmix.m").write_text("x = 1;\nfunction y = f(a)\ny = a;\nend\nz = 2;\n")
    s = Session.create_default()
    with pytest.raises(EvalError, match="local functions"):
        ReplSession(s).run_line(f"addpath('{tmp_path}'); badmix")


def test_cli_prints_no_traceback(tmp_path):
    (tmp_path / "lfscript.m").write_text(SCRIPT)
    out = subprocess.run([sys.executable, "-m", "openmatlab", "-e", f"run('{tmp_path / 'lfscript.m'}'); z"],
                         capture_output=True, text=True)
    assert "Traceback" not in out.stdout + out.stderr and "z =" in out.stdout and "ans =" not in out.stdout
