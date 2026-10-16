from __future__ import annotations

import os
from pathlib import Path

import pytest

from openmatlab.host.workbench import Workbench

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]

SCRIPT = "%% one\na = 1;\n%% two\nb = a + 1;\n%% three\nc = b * 10;\n"
BAD = "function bad_wf()\n  x = 1;\n  error('wf:e', 'oops');\nend\n"


@pytest.fixture
def wb(tmp_path):
    (tmp_path / "sec_wf.m").write_text(SCRIPT)
    (tmp_path / "bad_wf.m").write_text(BAD)
    w = Workbench.create(cwd=tmp_path)
    yield w
    if w.debug.is_paused():
        w.debug.quit()
    w.eval("dbclear all")


def _ed(text):
    from openmatlab.host.workbench import EditorPanel

    ed = EditorPanel()
    ed.set_text(text)
    return ed


def test_section_markers():
    assert _ed(SCRIPT).sections() == [(1, 2), (3, 4), (5, 6)]
    # leading code is its own section; '%%%' and '%%x' are not markers; indented '%%' is
    assert _ed("x=1;\n%% a\ny=2;\n  %%\nz=3;\n%%%no\n%%b\n").sections() == [(1, 1), (2, 3), (4, 7)]
    assert _ed("").sections() == [(1, 1)]


def test_run_section_and_advance(wb, tmp_path):
    ed = wb.documents.open_file(tmp_path / "sec_wf.m")
    ed.set_cursor_line(4)
    wb.eval("a = 5;")
    wb.run_section()
    assert wb.eval_value("b") == 6 and "c" not in wb.workspace.names()
    ed.set_cursor_line(1)
    for want in (3, 5, 5):  # the caret stays on the last section
        wb.run_and_advance()
        assert ed.cursor_line() == want
    assert wb.eval_value("c") == 20
    assert wb.command_window.history() == ["a = 5;"]  # editor runs are not history entries


def test_section_error_is_reported_not_raised(wb):
    ed = wb.documents.new_script()
    ed.set_text("error('boom')")
    wb.run_section()
    out = wb.command_window._stream.getvalue()
    assert "boom" in out and "Traceback" not in out


def test_run_file_with_breakpoint(wb, tmp_path):
    ed = wb.documents.open_file(tmp_path / "sec_wf.m")
    ed.toggle_breakpoint(6)
    wb.run_file()
    assert wb.debug.is_paused() and wb.debug.current_line() == 6
    wb.debug.continue_()
    assert wb.eval_value("c") == 20


def test_error_link(wb):
    out = wb.eval("bad_wf()")
    assert out.startswith("error: oops") and "Error in bad_wf (line 3)" in out and "Traceback" not in out
    path, line = wb.command_window.last_error_location()
    assert Path(path).name == "bad_wf.m" and line == 3
    ed = wb.open_error_link()
    assert ed.tab_title.startswith("bad_wf") and ed.tab_title() == ed.tab_title and ed.cursor_line() == 3
    wb.eval("undefined_wf_zz")  # no file frame -> no link
    assert wb.command_window.last_error_location() is None and wb.open_error_link() is None


def test_history_rerun(wb):
    wb.eval("q = 5;")
    wb.eval("q = q + 1;")
    wb.command_window.rerun_history(-1)
    wb.command_window.rerun_history(0)
    assert wb.eval_value("q") == 5
    assert wb.command_window.history()[-2:] == ["q = q + 1;", "q = 5;"]


def test_toolbar_has_section_actions(wb):
    assert {"Run Section", "Run and Advance"} <= set(wb.toolbar())


@pytest.mark.skipif(not os.environ.get("DISPLAY"), reason="needs a display for tk")
def test_tk_workflow_chrome(tmp_path):
    tk = pytest.importorskip("tkinter")
    from tkinter import ttk

    (tmp_path / "sec_wf.m").write_text(SCRIPT)
    w = Workbench.create(cwd=tmp_path)
    w.documents.open_file(tmp_path / "sec_wf.m")
    res = {}

    def walk(x):
        yield x
        for c in x.winfo_children():
            yield from walk(c)

    def drive(root):
        try:
            btn = next(b for b in walk(root) if isinstance(b, ttk.Button) and b.cget("text") == "Run and Advance")
            btn.invoke()
            res["a"] = w.eval_value("a")
            res["line"] = w.editor.cursor_line()
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
    assert res == {"a": 1, "line": 3}
