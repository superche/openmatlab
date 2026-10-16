"""Logical-mask assignment growth and logical results of cellfun / empty logical growth (#766)."""
import subprocess, sys
import pytest

pytestmark = pytest.mark.unit


def run(code):
    p = subprocess.run([sys.executable, "-m", "openmatlab", "-e", code], capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).rstrip()


def test_mask_assignment_grows():
    rc, out = run("x = []; x(logical([0 1 1])) = 5; disp(x); y = zeros(0,2); y(logical([1 0 1]),:) = 7; "
                  "disp(size(y)); disp(y(3,2)); z = 1:2; z(logical([0 0 0 1])) = 9; disp(z)")
    assert rc == 0 and out.split("\n") == ["   0   5   5", "   3   2", "7", "   1   2   0   9"], out


def test_logical_class_kept():
    rc, out = run("disp(class(cellfun(@isempty, {1,[]}))); disp(class(cellfun(@(x) x > 1, {1, 2}))); "
                  "s = false(1,0); s(end+1) = true; disp(class(s)); disp(class(cellfun(@numel, {1})))")
    assert rc == 0 and out.split("\n") == ["logical", "logical", "logical", "double"], out


def test_mask_read_out_of_range_still_errors():
    rc, out = run("x = 1:2; y = x(logical([0 0 1]))")
    assert rc != 0 and "Traceback" not in out, out


def test_cell_logical_mask_and_empty_cells_in_concat():
    rc, out = run("c = {1, 2, 3}; d = c(logical([1 0 1])); disp(numel(d)); disp(d{2}); "
                  "e = [cell(1,0), {4}, cell(0,1)]; disp(size(e)); x = c{logical([0 1 0])}; disp(x)")
    assert rc == 0 and out.split("\n") == ["2", "3", "   1   1", "2"], out
