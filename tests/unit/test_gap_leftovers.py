"""M7 close-out: colon, cputime, display, rmpath, path, print."""

from __future__ import annotations

import os

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _run(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s


def test_colon_and_cputime():
    s = _run("a = colon(1, 3); b = colon(1, 2, 7); t = cputime;")
    assert np.asarray(s.workspace.get("a").backend_buffer()).tolist() == [[1, 2, 3]]
    assert np.asarray(s.workspace.get("b").backend_buffer()).tolist() == [[1, 3, 5, 7]]
    assert np.asarray(s.workspace.get("t").backend_buffer()).item() >= 0


def test_path_rmpath_roundtrip(tmp_path):
    d = str(tmp_path)
    s = _run(f"addpath('{d}'); p1 = path; rmpath('{d}'); p2 = path;")
    assert d in s.workspace.get("p1").text and d not in s.workspace.get("p2").text


def test_print_exports_png(tmp_path):
    pytest.importorskip("matplotlib")
    f = str(tmp_path / "fig")
    _run(f"plot(1:3); print('-dpng', '{f}');")
    assert os.path.getsize(f + ".png") > 0


def test_display_prints_value(capsys):
    _run("display(7)")
    assert "7" in capsys.readouterr().out


@pytest.mark.parametrize("src", ["path({})", "path([])", "path(1,2)", "rmpath({})", "rmpath([])", "rmpath(1,2)"])
def test_path_rmpath_reject_non_char(src):
    s = _run("try, %s; ok = 0; catch e, ok = strcmp(e.identifier(end-12:end), ':InvalidInput'); end" % src)
    assert np.asarray(s.workspace.get("ok").backend_buffer()).item() == 1
