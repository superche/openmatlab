"""M11 D08 - Workbench debug UI on the headless model.

Gutter breakpoints map to dbstop/dbclear, the current-line marker follows the
paused frame, toolbar actions step/continue/quit, the stack selector rebinds the
Workspace panel. The debug API names are pinned by Epic D-E4's design.
"""

from pathlib import Path

from openmatlab.host.workbench import Workbench

SRC = "function y = wb_d08(x)\n  a = x + 1;\n  y = sub_d08(a);\nend\nfunction z = sub_d08(b)\n  z = b * 2;\nend\n"


def run(tmp: Path) -> dict:
    f = tmp / "wb_d08.m"
    f.write_text(SRC)
    wb = Workbench.create(cwd=tmp)
    ed = wb.documents.open_file(f)
    ed.toggle_breakpoint(2)
    out = {"g1": list(ed.breakpoints())}
    wb.eval("s_ = dbstatus('wb_d08'); n_ = s_(1).line;")
    out["g2"] = wb.eval_value("n_")
    wb.debug.run("r = wb_d08(1);")
    out["g3"] = int(wb.debug.is_paused())
    out["g4"] = wb.debug.current_line()
    wb.debug.step()
    out["g5"] = wb.debug.current_line()
    wb.debug.step_in()
    out["g6"] = wb.debug.current_line()
    out["g7"] = len(wb.debug.stack())
    out["g8"] = int("b" in wb.workspace.names())
    wb.debug.select_frame(1)
    out["g9"] = int("a" in wb.workspace.names())
    wb.debug.step_out()
    wb.debug.continue_()
    out["g10"] = int(wb.debug.is_paused())
    out["g11"] = wb.eval_value("r")
    ed.toggle_breakpoint(2)
    out["g12"] = len(ed.breakpoints())
    wb.debug.run("r = wb_d08(1);")
    out["g13"] = int(wb.debug.is_paused())
    ed.toggle_breakpoint(6)
    wb.debug.run("r2 = wb_d08(1);")
    wb.debug.quit()
    out["g14"] = int(wb.debug.is_paused())
    out["g15"] = int("Continue" in wb.debug_toolbar() and "Step In" in wb.debug_toolbar())
    return out
