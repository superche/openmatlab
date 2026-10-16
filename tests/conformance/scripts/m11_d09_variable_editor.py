"""M11 D09 - variable editor panel on the headless Workbench model."""

from pathlib import Path

from openmatlab.host.workbench import Workbench


def run(tmp: Path) -> dict:
    wb = Workbench.create(cwd=tmp)
    wb.eval("A = [1 2; 3 4]; s = 'hi'; c = {1, 'x'}; st.a = 5; T = table([1;2], [3;4]);")
    ve = wb.variable_editor
    out = {}
    v = ve.open("A")
    out["v1"] = list(v.size())
    out["v2"] = float(v.cell(2, 1))
    v.set_cell(2, 1, "30")
    out["v3"] = wb.eval_value("A(2,1)")
    out["v4"] = list(ve.open("s").size())
    vc = ve.open("c")
    out["v5"] = int(vc.cell(1, 2) == "'x'")
    vc.set_cell(1, 1, "7")
    out["v6"] = wb.eval_value("c{1}")
    vs = ve.open("st")
    out["v7"] = float(vs.cell(1, 2))
    vs.set_cell(1, 2, "9")
    out["v8"] = wb.eval_value("st.a")
    vt = ve.open("T")
    out["v9"] = int(vt.column_headers() == ["Var1", "Var2"])
    vt.set_cell(1, 2, "33")
    out["v10"] = wb.eval_value("T.Var2(1)")
    out["v11"] = len(ve.open_names())
    out["v12"] = int("Variables" in [r.name for r in wb.regions()])
    return out
