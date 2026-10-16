"""Variable editor panel (M11 D-E5, #702).

Host-owned, opened from the Workspace browser. ``VariableEditor.open(name)`` returns a
``VariableView`` grid over the variable in the *shown* workspace (the selected debug frame while
paused, else base): numeric/logical matrices, char, cell, scalar struct (Field | Value rows), and
table (one column per variable). ``set_cell(r, c, text)`` evaluates ``text`` as a MATLAB
expression in that workspace and writes it back with MATLAB indexed-assignment semantics
(``A(r,c) = …``, ``C{r,c} = …``, ``s.(field) = …``, ``T{r,c} = …``). Edits do not enter the
Command History. A bad edit raises ``VariableEditError`` and leaves the variable unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Tuple

import numpy as np


class VariableEditError(Exception):
    """A rejected edit (bad expression, wrong type, out-of-range cell); message is MATLAB-style."""


def _fmt_num(x) -> str:
    from openmatlab.runtime.table_value import _fmt_num as f

    return f(x)


def _elem_text(v) -> str:
    """How one cell-array / table / struct element appears in a variable-editor cell."""
    from openmatlab.host.display import _field_summary
    from openmatlab.runtime.char_value import CharValue

    if isinstance(v, CharValue) and not getattr(v, "is_string", False) and v.shape[0] <= 1:
        return f"'{v.text}'"
    if getattr(v, "is_string", False) and v.numel() == 1:
        g = v.data.flat[0]
        return "<missing>" if g is None else f'"{g}"'
    if hasattr(v, "backend_buffer") and not getattr(v, "is_object", False) and not getattr(v, "is_struct", False):
        try:
            a = np.asarray(v.backend_buffer())
        except Exception:
            a = None
        if a is not None and a.size == 1:
            return _fmt_num(a.reshape(-1)[0])
    if hasattr(v, "display_text") and getattr(v, "is_object", False) and getattr(v, "numel", lambda: 0)() == 1:
        return v.display_text().strip()
    return _field_summary(v)


@dataclass
class VariableView:
    """One open variable: a 1-based grid of display strings with write-back."""

    name: str
    editor: "VariableEditor"

    # -- reading -----------------------------------------------------------
    def value(self):
        ws = self.editor.workspace()
        if not ws.has(self.name) if hasattr(ws, "has") else self.name not in ws.names():
            raise VariableEditError(f"'{self.name}' is not in the current workspace.")
        return ws.get(self.name)

    def kind(self) -> str:
        v = self.value()
        from openmatlab.runtime.cell_value import CellValue
        from openmatlab.runtime.char_value import CharValue

        if getattr(v, "is_table", False):
            return "table"
        if getattr(v, "is_struct", False):
            if v.numel() != 1:
                return "struct_array"
            return "struct"
        if isinstance(v, CellValue):
            return "cell"
        if isinstance(v, CharValue) and not getattr(v, "is_string", False):
            return "char"
        if getattr(v, "is_string", False):
            return "string"
        if hasattr(v, "backend_buffer") and not getattr(v, "is_object", False):
            return "numeric"
        return "object"

    def size(self) -> Tuple[int, int]:
        """MATLAB size of the variable (rows, columns); a scalar struct shows as fields × 2."""
        v = self.value()
        k = self.kind()
        if k == "struct":
            return (len(v.fields), 2)
        if k == "table":
            return tuple(v.shape)
        sh = tuple(int(d) for d in getattr(v, "shape", (1, 1)))
        return (sh[0], int(np.prod(sh[1:])) if len(sh) > 1 else 1)

    def column_headers(self) -> List[str]:
        v = self.value()
        k = self.kind()
        if k == "table":
            return list(v.names)
        if k == "struct":
            return ["Field", "Value"]
        return [str(j + 1) for j in range(self.size()[1])]

    def row_headers(self) -> List[str]:
        v = self.value()
        if self.kind() == "table" and v.rownames:
            return list(v.rownames)
        if self.kind() == "struct":
            return list(v.fields)
        return [str(i + 1) for i in range(self.size()[0])]

    def _check(self, r: int, c: int, *, grow: bool = False) -> None:
        R, C = self.size()
        if r < 1 or c < 1 or int(r) != r or int(c) != c:
            raise VariableEditError("Row and column must be positive integers.")
        if not grow and (r > R or c > C):
            raise VariableEditError(f"Cell ({r},{c}) is outside the {R}×{C} variable.")

    def cell(self, r: int, c: int) -> str:
        self._check(r, c)
        v = self.value()
        k = self.kind()
        if k == "struct":
            f = v.fields[r - 1]
            return f if c == 1 else _elem_text(v.get(f))
        if k == "table":
            from openmatlab.runtime.cell_value import CellValue

            col = v.cols[c - 1]
            if isinstance(col, CellValue) and col.shape[1] == 1:
                return _elem_text(col.rows[r - 1][0])
            from openmatlab.libs.table_utils import _col_rows

            return self.editor._with_ev(lambda ev: _elem_text(_ix(ev, col, r)))
        if k == "cell":
            return _elem_text(v.rows[r - 1][c - 1])
        if k == "char":
            row = v.text.split("\n")[r - 1] if v.shape[0] > 1 else v.text
            return row[c - 1]
        if k == "string":
            g = np.asarray(v.data, dtype=object).reshape(v.shape)[r - 1, c - 1]
            return "<missing>" if g is None else str(g)
        if k == "numeric":
            a = np.asarray(v.backend_buffer())
            a = a.reshape(a.shape[0], -1, order="F") if a.ndim > 2 else a
            return _fmt_num(a[r - 1, c - 1])
        return self.editor._with_ev(lambda ev: _elem_text(_ix2(ev, v, r, c)))

    def grid(self) -> List[List[str]]:
        R, C = self.size()
        return [[self.cell(i + 1, j + 1) for j in range(C)] for i in range(R)]

    # -- writing -----------------------------------------------------------
    def set_cell(self, r: int, c: int, text: str) -> None:
        k = self.kind()
        if k in ("struct_array", "object"):
            raise VariableEditError(f"Editing a {self.value().matlab_class()} value in the Variables editor is not supported.")
        if k == "struct" and c != 2:
            raise VariableEditError("Only the Value column of a struct can be edited.")
        self._check(r, c, grow=k in ("numeric", "cell"))
        self.editor._assign(self, r, c, text)


def _num(x):
    from openmatlab.numerics.ndarray_value import NDArrayValue

    return NDArrayValue(np.array([[float(x)]]))


def _ix(ev, col, r):
    from openmatlab.runtime.table_subs import ix

    return ix(ev, col, [_num(r), None])


def _ix2(ev, v, r, c):
    from openmatlab.runtime.table_subs import ix

    return ix(ev, v, [_num(r), _num(c)])


@dataclass
class VariableEditor:
    """The Variables region: a set of open variable tabs over the shown workspace."""

    workspace_source: Callable[[], Any]
    functions_source: Callable[[], Any]
    _open: Dict[str, VariableView] = field(default_factory=dict)
    on_change: List[Callable[[str], None]] = field(default_factory=list)

    def workspace(self):
        return self.workspace_source()

    def open(self, name: str) -> VariableView:
        ws = self.workspace()
        if name not in ws.names():
            raise VariableEditError(f"'{name}' is not in the current workspace.")
        if name not in self._open:
            self._open[name] = VariableView(name=name, editor=self)
        return self._open[name]

    def close(self, name: str) -> None:
        self._open.pop(name, None)

    def open_names(self) -> List[str]:
        return list(self._open)

    # -- evaluation in the shown workspace ----------------------------------
    def _with_ev(self, fn):
        from openmatlab.runtime.evaluator import Evaluator

        s = self.functions_source()
        ev = Evaluator(workspace=self.workspace(), functions=s.functions, numerics=s.numerics, plots=s.plots,
                       display=s.display)
        from openmatlab.runtime import frames

        with frames.calling(ev):
            return fn(ev)

    def _parse_value(self, ev, text: str):
        from openmatlab.lang import ast_nodes as ast
        from openmatlab.lang.parser import parse

        src = (text or "").strip()
        if not src:
            raise VariableEditError("Enter a value or a MATLAB expression.")
        try:
            stmts = parse(src)
        except Exception as e:  # parser errors carry MATLAB-style text
            raise VariableEditError(f"Invalid expression: {e}") from None
        if len(stmts) != 1 or not isinstance(stmts[0], ast.ExprStmt):
            raise VariableEditError("Enter a single value or expression, not a statement.")
        return ev.eval_expr(stmts[0].expr)

    def _assign(self, view: VariableView, r: int, c: int, text: str) -> None:
        from openmatlab.runtime.evaluator import EvalError

        name = view.name
        kind = view.kind()

        def do(ev):
            base = self.workspace().get(name)
            val = self._parse_value(ev, text)
            if kind == "struct":
                return base.with_field(base.fields[r - 1], val)
            from openmatlab.runtime.table_subs import ix_asgn

            if kind == "char" and not (getattr(val, "text", None) is not None and len(val.text) == 1):
                raise VariableEditError("A character cell holds exactly one character.")
            return ix_asgn(ev, base, [_num(r), _num(c)], val, "{}" if kind in ("cell", "table") else "()")

        try:
            new = self._with_ev(do)
        except VariableEditError:
            raise
        except EvalError as e:
            raise VariableEditError(str(e)) from None
        self.workspace().set(name, new)
        for cb in list(self.on_change):
            cb(name)


def open_tk(parent, view: VariableView, on_written: Callable[[], None] = lambda: None):
    """A Variables tab body: a Treeview grid; double-click a cell to edit, Enter writes back."""
    import tkinter as tk
    from tkinter import ttk

    frame = ttk.Frame(parent)
    status = tk.StringVar(value="")
    tree = ttk.Treeview(frame, show="tree headings", height=12)
    tree.pack(fill="both", expand=True)
    ttk.Label(frame, textvariable=status, foreground="#a00").pack(anchor="w")

    def refresh():
        tree.delete(*tree.get_children())
        hdr = view.column_headers()
        tree["columns"] = [f"c{j}" for j in range(len(hdr))]
        tree.heading("#0", text="")
        tree.column("#0", width=60)
        for j, h in enumerate(hdr):
            tree.heading(f"c{j}", text=h)
            tree.column(f"c{j}", width=90)
        for i, (rh, row) in enumerate(zip(view.row_headers(), view.grid())):
            tree.insert("", "end", iid=str(i + 1), text=rh, values=row)

    def begin_edit(event):
        item = tree.identify_row(event.y)
        col = tree.identify_column(event.x)
        if not item or col in ("", "#0"):
            return
        r, c = int(item), int(col[1:])
        x, y, w, h = tree.bbox(item, col)
        ent = ttk.Entry(tree)
        ent.insert(0, view.cell(r, c))
        ent.place(x=x, y=y, width=w, height=h)
        ent.focus_set()

        def commit(_e=None):
            try:
                view.set_cell(r, c, ent.get())
                status.set("")
            except VariableEditError as err:
                status.set(str(err))
            ent.destroy()
            refresh()
            on_written()
        ent.bind("<Return>", commit)
        ent.bind("<Escape>", lambda _e: ent.destroy())

    tree.bind("<Double-1>", begin_edit)
    refresh()
    frame.refresh = refresh  # type: ignore[attr-defined]
    frame.tree = tree  # type: ignore[attr-defined]
    frame.begin_edit = begin_edit  # type: ignore[attr-defined]
    return frame
