"""M11 D10 - Workbench workflows: code sections, Run Section / Run and Advance,
run with breakpoints, error link -> file at line, Command History re-run."""

from pathlib import Path

from openmatlab.host.workbench import Workbench

SCRIPT = "%% one\na = 1;\n%% two\nb = a + 1;\n%% three\nc = b * 10;\n"
BAD = "function bad_d10()\n  x = 1;\n  error('d10:e', 'oops');\nend\n"


def run(tmp: Path) -> dict:
    (tmp / "sec_d10.m").write_text(SCRIPT)
    (tmp / "bad_d10.m").write_text(BAD)
    wb = Workbench.create(cwd=tmp)
    ed = wb.documents.open_file(tmp / "sec_d10.m")
    out = {"f1": len(ed.sections())}
    ed.set_cursor_line(2)
    wb.run_section()
    out["f2"] = wb.eval_value("a")
    out["f3"] = int("b" in wb.workspace.names())
    wb.run_and_advance()
    out["f4"] = ed.cursor_line()
    wb.run_and_advance()
    out["f5"] = wb.eval_value("b")
    wb.eval("clear all")
    ed.toggle_breakpoint(4)
    wb.run_file()
    out["f6"] = int(wb.debug.is_paused())
    out["f7"] = wb.debug.current_line()
    wb.debug.continue_()
    out["f8"] = wb.eval_value("c")
    wb.eval("bad_d10()")
    path, line = wb.command_window.last_error_location()
    out["f9"] = int(Path(path).name == "bad_d10.m")
    out["f10"] = line
    wb.open_error_link()
    out["f11"] = int(wb.editor.tab_title().startswith("bad_d10"))
    out["f12"] = wb.editor.cursor_line()
    wb.eval("q = 5;")
    wb.eval("q = q + 1;")
    wb.command_window.rerun_history(-1)
    out["f13"] = wb.eval_value("q")
    return out
