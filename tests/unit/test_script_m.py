"""Script .m parse + eval (Issue #35)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("numpy")

from openmatlab.host.repl import ReplSession
from openmatlab.lang.ast_nodes import FunctionDef
from openmatlab.runtime.functions import Script, eval_script, load_mfile, parse_mfile
from openmatlab.runtime.session import Session
from openmatlab.runtime.evaluator import Evaluator

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def test_load_function_still_works(tmp_path: Path):
    f = tmp_path / "add2.m"
    f.write_text("function y = add2(a, b)\ny = a + b;\nend\n")
    loaded = load_mfile(f)
    assert isinstance(loaded, FunctionDef)
    assert parse_mfile(f).name == "add2"


def test_load_script(tmp_path: Path):
    f = tmp_path / "init.m"
    f.write_text("a = 1;\nb = a + 2;\n")
    loaded = load_mfile(f)
    assert isinstance(loaded, Script)
    assert len(loaded.body) == 2


def test_eval_script_shares_workspace(tmp_path: Path):
    f = tmp_path / "init.m"
    f.write_text("a = 10;\nb = a + 5;\n")
    s = Session.create_default()
    script = load_mfile(f)
    assert isinstance(script, Script)
    ReplSession(s)  # ensure bind path exists
    s.functions.bind_runtime(s.numerics, s.plots)
    ev = Evaluator(
        workspace=s.workspace,
        functions=s.functions,
        numerics=s.numerics,
        plots=s.plots,
    )
    eval_script(script, ev)
    assert float(s.workspace.get("a").backend_buffer().reshape(-1)[0]) == 10.0
    assert float(s.workspace.get("b").backend_buffer().reshape(-1)[0]) == 15.0


def test_mixed_file_rejected(tmp_path: Path):
    # #529: a script followed by local functions is valid MATLAB (R2016b+);
    # code *after* a local function is still rejected.
    ok = tmp_path / "okscript.m"
    ok.write_text("x = 1;\nfunction y = f(a)\ny = a;\nend\n")
    loaded = load_mfile(ok)
    assert isinstance(loaded, Script) and [f.name for f in loaded.local_functions] == ["f"]
    f = tmp_path / "bad.m"
    f.write_text("x = 1;\nfunction y = f(a)\ny = a;\nend\nz = 2;\n")
    with pytest.raises(ValueError, match="Mixed|multiple"):
        load_mfile(f)
    g = tmp_path / "bad2.m"
    g.write_text("function y = f(a)\ny = a;\nend\nz = 2;\n")
    with pytest.raises(ValueError, match="Mixed|multiple"):
        load_mfile(g)
