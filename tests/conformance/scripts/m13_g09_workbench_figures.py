"""M13 G09 - Workbench output routing (#760) and docked figures on the headless model."""

from pathlib import Path

from openmatlab.host.workbench import Workbench


def run(tmp: Path) -> dict:
    wb = Workbench.create(cwd=tmp)
    (tmp / "s.m").write_text("fprintf('total = %d\\n', 7);\ndisp('hello')\nwarning('w:x','careful');\n")
    wb.run_file(tmp / "s.m")
    text = wb.command_window.text()
    out = {"w1": int("total = 7" in text), "w2": int("hello" in text), "w3": int("careful" in text)}
    wb.eval("figure('WindowStyle','docked');")
    figs = wb.figures.list()
    out["w4"] = int(len(figs) == 1 and figs[0].docked)
    out["w5"] = int(wb.figures.focused() == figs[0].number)
    return out
