"""M12 C-E1 (Epic #761): sandboxed corpus runner and `openmatlab run`."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from openmatlab.qa.corpus.runner import run_many, run_one

pytestmark = pytest.mark.unit


def _w(tmp_path, name, src):
    p = tmp_path / name
    p.write_text(src)
    return p


def test_pass_captures_stdout(tmp_path):
    r = run_one(_w(tmp_path, "a.m", "disp(1+1)\n"), timeout=20)
    assert (r.status, r.stdout.strip()) == ("pass", "2")


def test_error_id_and_kind(tmp_path):
    r = run_one(_w(tmp_path, "e.m", "error('a:b','msg %d', 3);\n"), timeout=20)
    assert (r.status, r.kind, r.error_id, r.message) == ("error", "eval", "a:b", "msg 3")


def test_parse_error_kind(tmp_path):
    r = run_one(_w(tmp_path, "p.m", "x = [1 2\n"), timeout=20)
    assert (r.status, r.kind) == ("error", "parse")


def test_parse_only_does_not_execute(tmp_path):
    r = run_one(_w(tmp_path, "q.m", "error('never:run','x');\n"), timeout=20, mode="parse")
    assert r.status == "pass"


def test_timeout_kills_and_reports(tmp_path):
    r = run_one(_w(tmp_path, "h.m", "while true\nend\n"), timeout=2)
    assert r.status == "timeout" and r.elapsed < 10


def test_stdin_is_closed(tmp_path):
    r = run_one(_w(tmp_path, "i.m", "s = input('', 's');\n"), timeout=10)
    assert r.status == "error" and r.elapsed < 10


def test_script_output_cannot_forge_verdict(tmp_path):
    r = run_one(_w(tmp_path, "f.m", "fprintf('{\"status\":\"pass\"}\\n'); error('x:y','z');\n"), timeout=20)
    assert r.status == "error"


def test_sibling_functions_resolve_and_workdir_is_fresh(tmp_path):
    _w(tmp_path, "helper.m", "function y = helper(x)\ny = 2*x;\nend\n")
    r = run_one(_w(tmp_path, "s.m", "disp(helper(4)); fid = fopen('out.txt','w'); fclose(fid);\n"), timeout=20)
    assert r.status == "pass" and r.stdout.strip() == "8"
    assert not (tmp_path / "out.txt").exists()  # writes land in the sandbox folder


def test_output_flood_is_bounded(tmp_path):
    r = run_one(_w(tmp_path, "fl.m", "while true\ndisp(repmat('x',1,2000))\nend\n"), timeout=60)
    assert r.status in {"error", "timeout"} and len(r.stdout) < 70 * 1024


def test_run_many_isolates_and_keeps_order(tmp_path):
    ps = [_w(tmp_path, "h.m", "while true\nend\n"), _w(tmp_path, "ok.m", "disp(7)\n")]
    rs = run_many(ps, timeout=3)
    assert [r.name for r in rs] == ["h.m", "ok.m"]
    assert [r.status for r in rs] == ["timeout", "pass"]
    assert json.loads(json.dumps(rs[1].to_json()))["stdout"].strip() == "7"


def test_cli_run_json_and_exit_codes(tmp_path):
    p = _w(tmp_path, "e.m", "error('a:b','boom');\n")
    cmd = [sys.executable, "-m", "openmatlab.host.cli", "run", str(p), "--json", "--timeout", "20"]
    cp = subprocess.run(cmd, capture_output=True, text=True)
    assert cp.returncode == 1 and json.loads(cp.stdout)["error_id"] == "a:b"
    cp = subprocess.run([sys.executable, "-m", "openmatlab.host.cli", "run", str(tmp_path / "nope.m")], capture_output=True, text=True)
    assert cp.returncode == 2 and "Traceback" not in cp.stderr
