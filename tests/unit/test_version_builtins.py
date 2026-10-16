import subprocess, sys
import pytest

pytestmark = pytest.mark.unit


def run(code):
    p = subprocess.run([sys.executable, "-m", "openmatlab", "-e", code], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


@pytest.mark.parametrize("code,want", [
    ("disp(verLessThan('matlab','8.4'))", "0"),
    ("disp(verLessThan('MATLAB','30.1'))", "1"),
    ("disp(version)", "24.2.0 (R2024b)"),
    ("disp(version('-release'))", "2024b"),
    ("s = ver('matlab'); disp(s.Name)", "MATLAB"),
    ("disp(isMATLABReleaseOlderThan('R2020a'))", "0"),
])
def test_release_queries(code, want):
    rc, out = run(code)
    assert rc == 0 and out.strip() == want


def test_unknown_toolbox_is_matlab_error():
    rc, out = run("verLessThan('signal','1')")
    assert rc != 0 and "Toolbox 'signal' not found." in out and "Traceback" not in out
