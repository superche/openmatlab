"""Workbench debug UI on the headless model, plus a tk smoke when a display exists (Epic #701)."""

from __future__ import annotations

import os

import pytest

from openmatlab.host.debug_ui import DebugError
from openmatlab.host.workbench import Workbench

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]

SRC = "function y = wbt(x)\n  a = x + 1;\n  y = subt(a);\nend\nfunction z = subt(b)\n  z = b * 2;\nend\n"


@pytest.fixture
def wb(tmp_path):
    (tmp_path / "wbt.m").write_text(SRC)
    w = Workbench.create(cwd=tmp_path)
    w.ed = w.documents.open_file(tmp_path / "wbt.m")
    yield w
    if w.debug.is_paused():
        w.debug.quit()
    w.eval("dbclear all")


def test_gutter_toggle_snaps_and_matches_dbstatus(wb):
    wb.ed.toggle_breakpoint(1)  # signature line snaps to the first statement
    assert wb.ed.breakpoints().tolist() == [[2]]
    wb.eval("s = dbstatus('wbt'); n = s(1).line;")
    assert wb.eval_value("n") == 2
    wb.eval("dbclear in wbt at 2")
    assert wb.ed.breakpoints().shape == (0, 0)


def test_paused_command_window_goes_to_k_prompt(wb):
    wb.ed.toggle_breakpoint(2)
    wb.debug.run("r = wbt(1);")
    assert wb.debug.is_paused() and wb.debug.current_line() == 2
    wb.eval("x = 41;")  # K>>: assignment in the paused frame takes effect on resume
    wb.debug.continue_()
    assert not wb.debug.is_paused()
    assert wb.eval_value("r") == 84


def test_stack_selector_and_step_out(wb):
    wb.ed.toggle_breakpoint(6)
    wb.debug.run("r = wbt(1);")
    names = [n for n, _f, _l in wb.debug.stack()]
    assert names == ["wbt>subt", "wbt"]
    assert wb.workspace.names() == ["b"]
    wb.debug.select_frame(1)
    assert wb.debug.current_line() == 3 and "a" in wb.workspace.names()
    wb.debug.step_out()  # pauses in the caller at the call line (MATLAB)
    assert wb.debug.is_paused() and wb.debug.current_line() == 3
    wb.debug.continue_()
    assert wb.eval_value("r") == 4


def test_misuse_is_a_clean_error(wb):
    with pytest.raises(DebugError):
        wb.debug.step()
    with pytest.raises(DebugError):
        wb.debug.select_frame(0)
    out = wb.debug.run("error('boom')") or wb.command_window._stream.getvalue()
    assert "boom" in out and "Traceback" not in out
    assert not wb.debug.is_paused()


def test_quit_and_toolbar(wb):
    wb.ed.toggle_breakpoint(2)
    wb.debug.run("r = wbt(1);")
    wb.debug.quit()
    assert not wb.debug.is_paused()
    assert wb.debug_toolbar() == ("Continue", "Step", "Step In", "Step Out", "Quit Debugging")


@pytest.mark.skipif(not os.environ.get("DISPLAY"), reason="needs a display for tk")
def test_tk_debug_chrome(tmp_path):
    tk = pytest.importorskip("tkinter")
    from tkinter import ttk

    (tmp_path / "wbk.m").write_text(SRC.replace("wbt", "wbk").replace("subt", "subk"))
    (tmp_path / "gok.m").write_text("r = wbk(1);\n")
    w = Workbench.create(cwd=tmp_path)
    w.documents.open_file(tmp_path / "wbk.m").toggle_breakpoint(2)
    w.documents.open_file(tmp_path / "gok.m")
    res = {}

    def walk(x):
        yield x
        for c in x.winfo_children():
            yield from walk(c)

    def btn(root, label):
        return next(b for b in walk(root) if isinstance(b, ttk.Button) and b.cget("text") == label)

    def drive(root):
        try:
            btn(root, "Run").invoke()
            res["paused"] = w.debug.is_paused()
            res["cur"] = any(t.tag_ranges("cur") for t in walk(root) if isinstance(t, tk.Text))
            btn(root, "Step").invoke()
            btn(root, "Step In").invoke()
            res["stack"] = list(next(b for b in walk(root) if isinstance(b, ttk.Combobox))["values"])
            btn(root, "Continue").invoke()
            res["r"] = w.eval_value("r")
        finally:
            root.destroy()

    orig = tk.Tk.mainloop

    def ml(self, n=0):
        self.after(100, lambda: drive(self))
        orig(self, n)

    try:
        tk.Tk.mainloop = ml
        try:
            w.run_tk()
        except tk.TclError as exc:
            pytest.skip(f"tk unavailable: {exc}")
    finally:
        tk.Tk.mainloop = orig
        w.eval("dbclear all")
    assert res["paused"] and res["cur"]
    assert res["stack"][0].startswith("wbk>subk")
    assert res["r"] == 4
