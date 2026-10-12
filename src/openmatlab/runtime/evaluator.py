"""AST evaluator — Array-first on Session numerics (+ optional plot surface)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional, Sequence

from openmatlab.lang import ast_nodes as ast
from openmatlab.lang.parser import parse
from openmatlab.numerics.backend import ArrayBackend
from openmatlab.runtime.functions import FunctionResolver
from openmatlab.runtime.value import Array, Value
from openmatlab.runtime.workspace import Workspace

if TYPE_CHECKING:
    from openmatlab.host.plot_surface import PlotSurface


class EvalError(Exception):
    pass


class _BreakSignal(Exception):
    """Internal: break leaves the innermost for/while."""


class _ContinueSignal(Exception):
    """Internal: continue skips to next iteration of innermost for/while."""


class _ReturnSignal(Exception):
    """Internal: return exits current function/script body."""


class Evaluator:
    """Walk AST against Workspace + ArrayBackend (+ optional PlotSurface)."""

    def __init__(
        self,
        workspace: Optional[Workspace] = None,
        functions: Optional[FunctionResolver] = None,
        numerics: Optional[ArrayBackend] = None,
        plots: Optional[Any] = None,
        display: Optional[Any] = None,
    ) -> None:
        self.workspace = workspace if workspace is not None else Workspace()
        self.functions = functions if functions is not None else FunctionResolver()
        if numerics is None:
            raise EvalError("Evaluator requires an ArrayBackend (Session.numerics)")
        self.numerics = numerics
        self.plots = plots
        # DisplayPolicy (host); None = silent (e.g. .m function bodies today).
        self.display = display
        self._loop_depth = 0
        self._return_ok = 0
        self._end_stack: list[float] = []

    def eval_source(self, source: str) -> Optional[Value]:
        stmts = parse(source)
        return self.eval_program(stmts)

    def eval_program(self, stmts: Sequence[ast.Stmt]) -> Optional[Value]:
        last: Optional[Value] = None
        self._return_ok += 1
        try:
            try:
                for stmt in stmts:
                    last = self.eval_stmt(stmt)
            except _ReturnSignal:
                return last
            except _BreakSignal:
                raise EvalError("break outside of a for or while loop") from None
            except _ContinueSignal:
                raise EvalError("continue outside of a for or while loop") from None
            return last
        finally:
            self._return_ok -= 1

    def eval_stmt(self, stmt: ast.Stmt) -> Value:
        value = self._exec_stmt(stmt)
        if self.display is not None:
            self._display_stmt(stmt, value)
        return value

    def _display_stmt(self, stmt: ast.Stmt, value: Value) -> None:
        """MATLAB display: each simple statement, where it runs; never for blocks.

        Assignments show the assigned variable(s) and never touch ``ans``; a bare
        variable name shows under its own name; any other expression binds ``ans``.
        """
        d = self.display
        show = d.should_print(getattr(stmt, "suppress", True))
        if isinstance(stmt, ast.Assign):
            names: Sequence[str] = (stmt.name,)
        elif isinstance(stmt, (ast.ArrayAssign, ast.CellAssign)):
            base = stmt.target.target
            names = (base.id,) if isinstance(base, ast.Name) else ()
        elif isinstance(stmt, ast.MultiAssign):
            names = stmt.names
        elif isinstance(stmt, ast.ExprStmt):
            if isinstance(stmt.expr, ast.Name) and stmt.expr.id in self.workspace:
                if show:
                    d.show(value, name=stmt.expr.id)
                return
            d.bind_ans(value)
            if show:
                d.show(value)
            return
        else:
            return
        if show:
            for n in names:
                d.show(self.workspace.get(n), name=n)

    def _exec_stmt(self, stmt: ast.Stmt) -> Value:
        if isinstance(stmt, ast.Assign):
            value = self.eval_expr(stmt.value)
            self.workspace.set(stmt.name, value)
            return value
        if isinstance(stmt, ast.CellAssign):
            return self._eval_cell_assign(stmt)
        if isinstance(stmt, ast.ArrayAssign):
            return self._eval_array_assign(stmt)
        if isinstance(stmt, ast.MultiAssign):
            return self._eval_multi_assign(stmt)
        if isinstance(stmt, ast.IfStmt):
            return self._eval_if(stmt)
        if isinstance(stmt, ast.ForStmt):
            return self._eval_for(stmt)
        if isinstance(stmt, ast.WhileStmt):
            return self._eval_while(stmt)
        if isinstance(stmt, ast.BreakStmt):
            if self._loop_depth <= 0:
                raise EvalError("break outside of a for or while loop")
            raise _BreakSignal()
        if isinstance(stmt, ast.ContinueStmt):
            if self._loop_depth <= 0:
                raise EvalError("continue outside of a for or while loop")
            raise _ContinueSignal()
        if isinstance(stmt, ast.ReturnStmt):
            if self._return_ok <= 0:
                raise EvalError("return outside of a function or script")
            raise _ReturnSignal()
        if isinstance(stmt, ast.SwitchStmt):
            return self._eval_switch(stmt)
        if isinstance(stmt, ast.ExprStmt):
            return self.eval_expr(stmt.expr)
        if isinstance(stmt, ast.FunctionDef):
            raise EvalError(
                "function definitions are only valid in .m files on the path"
            )
        raise EvalError(f"Unknown statement: {type(stmt)!r}")

    def eval_expr(self, expr: ast.Expr) -> Value:
        if isinstance(expr, ast.FuncHandleExpr):
            from openmatlab.runtime.function_handle import FunctionHandleValue
            try:
                fn = self.functions.resolve(expr.name)
            except Exception as e:
                raise EvalError(f"function handle: undefined function '{expr.name}'") from e
            return FunctionHandleValue(name=expr.name, fn=fn)
        if isinstance(expr, ast.AnonFuncExpr):
            return self._make_anon(expr)
        if isinstance(expr, ast.EndExpr):
            if not self._end_stack:
                raise EvalError("end outside of an indexing expression")
            return self.numerics.from_scalar(self._end_stack[-1])
        if isinstance(expr, ast.NumberLiteral):
            return self.numerics.from_scalar(expr.value)
        if isinstance(expr, ast.StringLiteral):
            from openmatlab.runtime.char_value import CharValue

            return CharValue(expr.value)
        if isinstance(expr, ast.Name):
            try:
                return self.workspace.get(expr.id)
            except KeyError:
                # bare i / j → imaginary unit when unbound
                if expr.id in ("i", "j"):
                    import numpy as np
                    from openmatlab.numerics.ndarray_value import NDArrayValue
                    return NDArrayValue(np.asarray([[1j]]))
                # bare script on path before treating as function
                mfile = None
                try:
                    mfile = self.functions._find(expr.id)  # type: ignore[attr-defined]
                except Exception:
                    mfile = None
                if mfile is not None:
                    from openmatlab.runtime.functions import Script, eval_script, load_mfile
                    loaded = load_mfile(mfile)
                    if isinstance(loaded, Script):
                        eval_script(loaded, self)
                        return self.numerics.from_scalar(0.0)
                    # else fall through to function resolve via _invoke_call
                # MATLAB: unbound name may be a zero-arg function/builtin (NaN, pi, …)
                try:
                    results = self._invoke_call(expr, [], nargout=1)
                except (EvalError, ValueError, LookupError):
                    results = None
                if results is not None:
                    if not results:
                        return self.numerics.from_nested([])
                    return results[0]
                raise EvalError(f"Undefined variable: {expr.id}")
        if isinstance(expr, ast.UnaryOp):
            v = self._require_array(self.eval_expr(expr.operand), "unary")
            if expr.op == "+":
                return v
            if expr.op == "-":
                z = self.numerics.from_scalar(0.0)
                return self.numerics.sub(z, v)
            if expr.op == "~":
                return self._logical(~self._bool_buf(v))
            raise EvalError(f"Unknown unary op: {expr.op}")
        if isinstance(expr, ast.BinOp):
            return self._eval_binop(expr)
        if isinstance(expr, ast.CellLiteral):
            return self._eval_cell_literal(expr)
        if isinstance(expr, ast.MatrixLiteral):
            return self._eval_matrix(expr)
        if isinstance(expr, ast.ColonExpr):
            return self._eval_colon(expr)
        if isinstance(expr, ast.TransposeExpr):
            return self.numerics.transpose(
                self._require_array(self.eval_expr(expr.operand), "transpose"),
                conjugate=expr.conjugate,
            )
        if isinstance(expr, ast.CellIndexExpr):
            return self._eval_cell_index(expr)
        if isinstance(expr, ast.IndexExpr):
            return self._eval_call_or_index(expr.target, list(expr.indices))
        if isinstance(expr, ast.CallExpr):
            return self._eval_call_or_index(expr.func, list(expr.args))
        raise EvalError(f"Unknown expression: {type(expr)!r}")


    def _eval_cell_literal(self, expr: "ast.CellLiteral") -> Value:
        from openmatlab.runtime.cell_value import CellValue

        if not expr.rows:
            return CellValue(rows=tuple())
        rows = []
        width = None
        for row in expr.rows:
            vals = [self.eval_expr(cell) for cell in row]
            if width is None:
                width = len(vals)
            elif len(vals) != width:
                raise EvalError("Cell literal rows must have equal length")
            rows.append(tuple(vals))
        return CellValue(rows=tuple(rows))



    def _eval_cell_index(self, expr: "ast.CellIndexExpr") -> Value:
        from openmatlab.runtime.cell_value import CellValue

        target = self.eval_expr(expr.target)
        if not isinstance(target, CellValue):
            raise EvalError(
                f"cell index: expected cell, got {type(target).__name__}"
            )
        idxs = list(expr.indices)
        if len(idxs) == 1:
            ri, cj = self._cell_subscript_lists(target, idxs, "cell index")
            # linear: ri/cj are paired positions
            if len(ri) == 1:
                return target.get(ri[0], cj[0])
            # pack as column cell of contents
            return CellValue(rows=tuple((target.get(i, j),) for i, j in zip(ri, cj)))
        rows_i, cols_j = self._cell_subscript_lists(target, idxs, "cell index")
        if len(rows_i) == 1 and len(cols_j) == 1:
            return target.get(rows_i[0], cols_j[0])
        grid = tuple(
            tuple(target.get(i, j) for j in cols_j) for i in rows_i
        )
        return CellValue(rows=grid)


    def _eval_array_assign(self, stmt: "ast.ArrayAssign") -> Value:
        from openmatlab.runtime.cell_value import CellValue

        target_expr = stmt.target.target
        if not isinstance(target_expr, ast.Name):
            raise EvalError("array assign: LHS must be name(...) in this MVP")
        name = target_expr.id
        try:
            arr = self.workspace.get(name)
        except KeyError as exc:
            raise EvalError(f"Undefined variable: {name}") from exc
        rhs_val = self.eval_expr(stmt.value)
        # c(i)=[] delete on cell arrays
        if isinstance(arr, CellValue):
            return self._eval_cell_paren_delete_or_assign(
                name, arr, list(stmt.target.indices), rhs_val
            )
        arr_a = self._require_array(arr, "array assign")
        idxs = self._eval_subscripts(
            arr_a, list(stmt.target.indices), label="array assign"
        )
        rhs = self._require_array(rhs_val, "array assign")
        try:
            new_arr = self.numerics.set_index(arr_a, idxs, rhs)
        except Exception as exc:  # NumericsError
            raise EvalError(f"array assign: {exc}") from exc
        self.workspace.set(name, new_arr)
        return rhs

    def _eval_cell_paren_delete_or_assign(
        self,
        name: str,
        cell: "object",
        idx_exprs: list,
        rhs_val: Value,
    ) -> Value:
        """c(i)=[] / c(i,j)=[] delete; c(i)={v} / c(i,j)={v} replace content."""
        from openmatlab.runtime.cell_value import CellValue

        assert isinstance(cell, CellValue)

        # Non-empty cell RHS → assign into paren slice (grow if needed)
        if isinstance(rhs_val, CellValue):
            if not (1 <= len(idx_exprs) <= 2):
                raise EvalError("cell () assign: only 1 or 2 subscripts")
            # Grow only when a single OOB subscript needs expansion
            try:
                cell = self._cell_grow_for_assign(cell, idx_exprs)
            except EvalError:
                # non-scalar indices: no grow via content helper; require in-bounds
                pass
            if len(idx_exprs) == 1:
                ri, cj = self._cell_subscript_lists(cell, idx_exprs, "cell () assign")
                n = len(ri)
                if rhs_val.numel() == 1 and n == 1:
                    self.workspace.set(
                        name, cell.with_set(ri[0], cj[0], rhs_val.get(0, 0))
                    )
                    return rhs_val
                if rhs_val.numel() != n:
                    raise EvalError(
                        f"cell () assign: RHS numel ({rhs_val.numel()}) != LHS ({n})"
                    )
                # RHS linear column-major into selected positions
                flat_rhs = []
                rr, cc = rhs_val.shape
                for j in range(cc):
                    for i in range(rr):
                        flat_rhs.append(rhs_val.get(i, j))
                new_cell = cell
                for (i0, j0), val in zip(zip(ri, cj), flat_rhs):
                    new_cell = new_cell.with_set(i0, j0, val)
                self.workspace.set(name, new_cell)
                return rhs_val
            rows_i, cols_j = self._cell_subscript_lists(
                cell, idx_exprs, "cell () assign"
            )
            n = len(rows_i) * len(cols_j)
            if rhs_val.numel() == 1 and n == 1:
                self.workspace.set(
                    name,
                    cell.with_set(rows_i[0], cols_j[0], rhs_val.get(0, 0)),
                )
                return rhs_val
            if rhs_val.shape != (len(rows_i), len(cols_j)) and rhs_val.numel() != n:
                raise EvalError("cell () assign: RHS shape mismatch")
            new_cell = cell
            # fill column-major from RHS
            flat_rhs = []
            rr, cc = rhs_val.shape
            for j in range(cc):
                for i in range(rr):
                    flat_rhs.append(rhs_val.get(i, j))
            k = 0
            for j0 in cols_j:
                for i0 in rows_i:
                    new_cell = new_cell.with_set(i0, j0, flat_rhs[k])
                    k += 1
            self.workspace.set(name, new_cell)
            return rhs_val

        # Empty numeric → delete
        # MATLAB: c(i) = non-cell is an error unless it is [] (delete)
        not_possible = EvalError(
            f"Conversion to cell from {rhs_val.matlab_class()} is not possible."
        )
        try:
            rhs_arr = self._require_array(rhs_val, "cell () assign")
        except EvalError as exc:
            raise not_possible from exc
        if rhs_arr.numel() != 0:
            raise not_possible
        if not (1 <= len(idx_exprs) <= 2):
            raise EvalError("cell () delete: only 1 or 2 subscripts")
        rows, cols = cell.shape
        if len(idx_exprs) == 1:
            drop = set(self._cell_linear_delete_positions(cell, idx_exprs[0]))
        else:
            i0, j0 = self._cell_subscripts(cell, idx_exprs, "cell () delete")
            drop = {i0 + j0 * rows}  # column-major linear 0-based
        flat = [
            cell.get(i, j)
            for j in range(cols)
            for i in range(rows)
            if i + j * rows not in drop
        ]
        if not flat:
            new_cell = CellValue.empty(0, 0)
        elif rows == 1 and cols >= 1:
            new_cell = CellValue(rows=(tuple(flat),))
        else:
            # column vector residual (incl. former 2-D)
            new_cell = CellValue(rows=tuple((v,) for v in flat))
        self.workspace.set(name, new_cell)
        return rhs_val

    def _cell_linear_delete_positions(self, cell, aexpr: ast.Expr) -> list:
        """0-based linear positions for c(idx)=[]: numeric indices or logical mask."""
        import numpy as np

        n = cell.numel()
        if self._is_bare_colon(aexpr):
            return list(range(n))
        self._end_stack.append(float(n))
        try:
            v = self._require_array(self.eval_expr(aexpr), "cell () delete")
        finally:
            self._end_stack.pop()
        buf = np.asarray(v.backend_buffer())
        if buf.dtype == np.bool_:
            mask = buf.reshape(-1, order="F")
            if mask.size > n and mask[n:].any():
                raise EvalError(f"cell () delete: index exceeds {n}")
            return [int(k) for k in np.flatnonzero(mask[:n])]
        flat = buf.astype(np.float64).reshape(-1, order="F")
        if np.any(flat != np.floor(flat)) or np.any(flat < 1):
            raise EvalError("cell () delete: indices must be positive integers")
        if np.any(flat > n):
            raise EvalError(f"cell () delete: index exceeds {n}")
        return [int(k) - 1 for k in flat]

    def _eval_cell_assign(self, stmt: "ast.CellAssign") -> Value:
        from openmatlab.runtime.cell_value import CellValue

        target_expr = stmt.target.target
        if not isinstance(target_expr, ast.Name):
            raise EvalError("cell assign: LHS must be name{...} in this MVP")
        name = target_expr.id
        try:
            cell = self.workspace.get(name)
        except KeyError as exc:
            raise EvalError(f"Undefined variable: {name}") from exc
        if not isinstance(cell, CellValue):
            raise EvalError(
                f"cell assign: expected cell, got {type(cell).__name__}"
            )
        value = self.eval_expr(stmt.value)
        cell = self._cell_grow_for_assign(cell, list(stmt.target.indices))
        i0, j0 = self._cell_subscripts(
            cell, list(stmt.target.indices), "cell assign"
        )
        self.workspace.set(name, cell.with_set(i0, j0, value))
        return value

    def _cell_grow_for_assign(self, cell: "object", idx_exprs: list) -> "object":
        """Expand cell grid so subscripts fit (MATLAB c{k}= grow)."""
        from openmatlab.runtime.cell_value import CellValue
        from openmatlab.numerics.ndarray_value import NDArrayValue
        import numpy as np

        assert isinstance(cell, CellValue)
        rows, cols = cell.shape
        blank = NDArrayValue(np.zeros((0, 0), dtype=np.float64))
        idxs = [self.eval_expr(i) for i in idx_exprs]

        def _as_int(v: Value) -> int:
            arr = self._require_array(v, "cell assign")
            if not arr.is_scalar():
                raise EvalError("cell assign: expected scalar index")
            x = float(arr.backend_buffer().reshape(-1)[0])
            if x != int(x) or x < 1:
                raise EvalError("cell assign: indices must be positive integers")
            return int(x)

        if len(idxs) == 1:
            k = _as_int(idxs[0])
            if k <= cell.numel() and not (rows == 0 and cols == 0):
                return cell  # in-bounds linear — no reshape
            if rows == 0 and cols == 0:
                need_r, need_c = 1, k
            elif rows == 1:
                need_r, need_c = 1, max(cols, k)
            elif cols == 1:
                need_r, need_c = max(rows, k), 1
            else:
                # OOB linear on 2-D cell → column of length k
                flat = []
                for j in range(cols):
                    for i in range(rows):
                        flat.append(cell.get(i, j))
                while len(flat) < k:
                    flat.append(blank)
                return CellValue(rows=tuple((v,) for v in flat[:k]))
        elif len(idxs) == 2:
            i = _as_int(idxs[0])
            j = _as_int(idxs[1])
            if i <= rows and j <= cols:
                return cell
            need_r, need_c = max(rows, i), max(cols, j)
        else:
            raise EvalError("cell assign: only 1 or 2 subscripts supported")

        if need_r == rows and need_c == cols:
            return cell
        grid = [[blank for _ in range(need_c)] for _ in range(need_r)]
        for i in range(min(rows, need_r)):
            for j in range(min(cols, need_c)):
                grid[i][j] = cell.get(i, j)
        return CellValue(rows=tuple(tuple(r) for r in grid))

    def _cell_subscript_lists(
        self, cell: "object", idx_exprs: list, label: str
    ) -> tuple:
        """Return 0-based row list and col list (supports end and :)."""
        from openmatlab.runtime.cell_value import CellValue
        import numpy as np
        from openmatlab.numerics.ndarray_value import NDArrayValue

        assert isinstance(cell, CellValue)
        if not idx_exprs:
            raise EvalError(f"{label}: missing indices")
        rows, cols = cell.shape
        if rows == 0 and cols == 0:
            raise EvalError(f"{label}: empty cell")

        def _eval_dim(aexpr, dim_size: int, linear_numel: int | None = None):
            end_val = float(linear_numel if linear_numel is not None else dim_size)
            if (
                isinstance(aexpr, ast.ColonExpr)
                and aexpr.start is None
                and aexpr.stop is None
            ):
                return list(range(dim_size))
            self._end_stack.append(end_val)
            try:
                v = self._require_array(self.eval_expr(aexpr), label)
            finally:
                self._end_stack.pop()
            buf = np.asarray(v.backend_buffer(), dtype=np.float64).reshape(-1)
            if buf.size == 0:
                return []
            if np.any(buf != np.floor(buf)) or np.any(buf < 1):
                raise EvalError(f"{label}: indices must be positive integers")
            out = []
            limit = linear_numel if linear_numel is not None else dim_size
            for x in buf:
                k = int(x)
                if k > limit:
                    raise EvalError(f"{label}: index {k} exceeds {limit}")
                out.append(k - 1)
            return out

        if len(idx_exprs) == 1:
            # linear: end = numel; colon → all; multi → column-major positions
            ks = _eval_dim(idx_exprs[0], cell.numel(), linear_numel=cell.numel())
            pairs = [((k % rows), (k // rows)) for k in ks]
            if len(pairs) == 1:
                return [pairs[0][0]], [pairs[0][1]]
            # multi linear → treat as list of cells packed as column
            return [p[0] for p in pairs], [p[1] for p in pairs]
        if len(idx_exprs) == 2:
            ri = _eval_dim(idx_exprs[0], rows)
            cj = _eval_dim(idx_exprs[1], cols)
            return ri, cj
        raise EvalError(f"{label}: only 1 or 2 subscripts supported")

    def _cell_subscripts(
        self, cell: "object", idx_exprs: list, label: str
    ) -> tuple:
        """Return single 0-based (i, j) for scalar cell indexing."""
        ri, cj = self._cell_subscript_lists(cell, idx_exprs, label)
        if len(idx_exprs) == 1:
            # linear multi not allowed for scalar API
            if len(ri) != 1:
                raise EvalError(f"{label}: expected scalar index")
            return ri[0], cj[0]
        if len(ri) != 1 or len(cj) != 1:
            raise EvalError(f"{label}: expected scalar index")
        return ri[0], cj[0]



    def _eval_subscripts(
        self, target: Array, arg_exprs: List[ast.Expr], *, label: str
    ) -> List[Array]:
        """Eval index exprs with `end` bound per MATLAB dim / numel rules."""
        n = len(arg_exprs)
        idxs: List[Array] = []
        for i, aexpr in enumerate(arg_exprs):
            if n == 1:
                end_val = float(target.numel())
            else:
                shape = target.shape
                if i >= len(shape):
                    raise EvalError(f"{label}: too many subscripts")
                end_val = float(shape[i])
            # Bare ":" → 1:end for this dim (or 1:numel for linear)
            if (
                isinstance(aexpr, ast.ColonExpr)
                and aexpr.start is None
                and aexpr.stop is None
            ):
                idxs.append(self.numerics.colon(1.0, end_val, 1.0))
                continue
            self._end_stack.append(end_val)
            try:
                idxs.append(self._require_array(self.eval_expr(aexpr), label))
            finally:
                self._end_stack.pop()
        return idxs

    def _require_array(self, val: Value, ctx: str) -> Array:
        if not isinstance(val, Array):
            raise EvalError(f"{ctx}: expected Array, got {type(val).__name__}")
        return val

    def _eval_multi_assign(self, stmt: ast.MultiAssign) -> Value:
        nargout = len(stmt.names)
        if nargout < 1:
            raise EvalError("multi-assign: empty output list")
        expr = stmt.value
        if isinstance(expr, ast.IndexExpr):
            target_expr, arg_exprs = expr.target, list(expr.indices)
        elif isinstance(expr, ast.CallExpr):
            target_expr, arg_exprs = expr.func, list(expr.args)
        else:
            raise EvalError("multi-assign RHS must be a function call")
        results = self._invoke_call(target_expr, arg_exprs, nargout=nargout)
        if len(results) < nargout:
            raise EvalError(
                f"multi-assign: expected {nargout} outputs, got {len(results)}"
            )
        for name, val in zip(stmt.names, results):
            self.workspace.set(name, val)
        return results[0]

    def _make_anon(self, expr: ast.AnonFuncExpr):
        """Anonymous function: snapshot visible variables now (MATLAB capture)."""
        from openmatlab.runtime.function_handle import FunctionHandleValue

        captured = {n: self.workspace.get(n) for n in self.workspace.names()}
        params = tuple(expr.params)

        def call(args, *, nargout: int = 1):
            if len(args) > len(params):
                raise EvalError("Too many input arguments.")
            ws = Workspace()
            for n, v in captured.items():
                ws.set(n, v)
            for n, v in zip(params, args):
                ws.set(n, v)
            ev = Evaluator(
                workspace=ws, functions=self.functions, numerics=self.numerics, plots=self.plots
            )
            return (ev.eval_expr(expr.body),)

        return FunctionHandleValue(name=expr.text, fn=call)

    @staticmethod
    def _is_bare_colon(expr: ast.Expr) -> bool:
        return isinstance(expr, ast.ColonExpr) and expr.start is None and expr.stop is None

    def _eval_call_or_index(self, target_expr: ast.Expr, arg_exprs: List[ast.Expr]) -> Value:
        results = self._invoke_call(target_expr, arg_exprs, nargout=1)
        if results is None:
            target = self.eval_expr(target_expr)
            from openmatlab.runtime.cell_value import CellValue
            from openmatlab.runtime.function_handle import FunctionHandleValue

            if isinstance(target, CellValue):
                return self._eval_cell_paren_index(target, arg_exprs)
            if isinstance(target, FunctionHandleValue):
                outs = target.call(self._eval_call_args(arg_exprs), nargout=1)
                if not outs:
                    raise EvalError("function handle call returned no value")
                return outs[0]
            target_a = self._require_array(target, "index")
            idxs = self._eval_subscripts(target_a, arg_exprs, label="index")
            out = self.numerics.index(target_a, idxs)
            if len(arg_exprs) == 1 and self._is_bare_colon(arg_exprs[0]):
                # A(:) is always a numel×1 column (MATLAB), even for rows / empties
                import numpy as np
                from openmatlab.numerics.ndarray_value import NDArrayValue

                out = NDArrayValue(np.asarray(out.backend_buffer()).reshape(-1, 1))
            return out
        if not results:
            return self.numerics.from_nested([])
        return results[0]

    def _eval_cell_paren_index(
        self, cell: "object", arg_exprs: List[ast.Expr]
    ) -> Value:
        """c(i) / c(:,j) → sub-cell (paren slice, not content)."""
        from openmatlab.runtime.cell_value import CellValue

        assert isinstance(cell, CellValue)
        idxs = list(arg_exprs)
        if len(idxs) == 1:
            ri, cj = self._cell_subscript_lists(cell, idxs, "cell () index")
            # linear positions → column cell of 1×1 contents wrappers? MATLAB: c(1:2) is 1×2 or 2×1 subcell of cells
            # Each selected element stays as cell content inside the subarray
            if len(ri) == 1:
                return CellValue(rows=((cell.get(ri[0], cj[0]),),))
            return CellValue(rows=tuple((cell.get(i, j),) for i, j in zip(ri, cj)))
        rows_i, cols_j = self._cell_subscript_lists(cell, idxs, "cell () index")
        grid = tuple(tuple(cell.get(i, j) for j in cols_j) for i in rows_i)
        return CellValue(rows=grid)


    def _eval_call_args(self, arg_exprs: List[ast.Expr]) -> list:
        """Evaluate call args with cell CSL expansion c{:} / c{:,k} pack→list."""
        from openmatlab.runtime.cell_value import CellValue

        out: list = []
        for a in arg_exprs:
            # CSL: content index with only bare colon(s) or multi result cell from {}
            if isinstance(a, ast.CellIndexExpr):
                val = self.eval_expr(a)
                # If multi-content packed as cell (from colon), expand
                bare = all(
                    isinstance(ix, ast.ColonExpr)
                    and ix.start is None
                    and ix.stop is None
                    for ix in a.indices
                )
                if bare and isinstance(val, CellValue):
                    rows, cols = val.shape
                    for j in range(cols):
                        for i in range(rows):
                            out.append(val.get(i, j))
                    continue
                out.append(val)
                continue
            out.append(self.eval_expr(a))
        return out

    def _invoke_call(
        self,
        target_expr: ast.Expr,
        arg_exprs: List[ast.Expr],
        *,
        nargout: int,
    ):
        """Return output sequence for a function call, or None if indexing."""
        if not (
            isinstance(target_expr, ast.Name)
            and not self._name_bound(target_expr.id)
        ):
            if nargout != 1:
                raise EvalError("multi-assign RHS must be a function call")
            return None
        n = target_expr.id
        key = n.lower()
        if key == "plot":
            if nargout != 1:
                raise EvalError("plot: only one output supported")
            return (self._builtin_plot(arg_exprs),)
        if key == "addpath":
            if nargout != 1:
                raise EvalError("addpath: only one output supported")
            return (self._builtin_addpath(arg_exprs),)
        if key == "which":
            if nargout != 1:
                raise EvalError("which: only one output supported")
            return (self._builtin_which(arg_exprs),)
        if key in ("show", "drawnow"):
            if nargout != 1:
                raise EvalError(f"{key}: only one output supported")
            return (self._builtin_show(arg_exprs),)
        if key == "run":
            if nargout != 1:
                raise EvalError("run: only one output supported")
            return (self._builtin_run(arg_exprs),)
        try:
            fn = self.functions.resolve(n)
        except LookupError as exc:
            raise EvalError(str(exc)) from exc
        args = self._eval_call_args(arg_exprs)
        try:
            results = list(fn(args, nargout=nargout))
        except ValueError as exc:  # builtin argument errors (e.g. BuiltinError)
            msg = str(exc)
            raise EvalError(msg if msg.startswith(f"{n}:") else f"{n}: {msg}") from exc
        for i, out in enumerate(results):
            if not isinstance(out, Value):
                raise EvalError(f"{n}: output {i} is not a Value")
        return results

    def _string_arg(self, expr: ast.Expr, fname: str) -> str:
        from openmatlab.runtime.char_value import CharValue

        val = self.eval_expr(expr)
        if isinstance(val, CharValue):
            return val.text
        raise EvalError(f"{fname}: expected char/string argument")

    def _name_bound(self, name: str) -> bool:
        try:
            self.workspace.get(name)
            return True
        except KeyError:
            return False

    def _builtin_plot(self, arg_exprs: List[ast.Expr]) -> Array:
        if self.plots is None:
            raise EvalError("plot: no PlotSurface on this Session")
        args = [
            self._require_array(self.eval_expr(a), "plot") for a in arg_exprs
        ]
        handle = self.plots.plot(*args)
        try:
            return self.numerics.from_scalar(float(handle))
        except (TypeError, ValueError):
            return self.numerics.from_scalar(1.0)

    def _builtin_addpath(self, arg_exprs: List[ast.Expr]) -> Value:
        from openmatlab.runtime.char_value import CharValue

        if not arg_exprs:
            raise EvalError("addpath: expected at least one directory")
        if self.functions.path is None:
            raise EvalError("addpath: no ToolboxPath on FunctionResolver")
        last = ""
        for a in arg_exprs:
            last = self._string_arg(a, "addpath")
            self.functions.path.addpath(last)
        return CharValue(last)

    def _builtin_which(self, arg_exprs: List[ast.Expr]) -> Value:
        from openmatlab.runtime.char_value import CharValue

        if len(arg_exprs) != 1:
            raise EvalError("which: expected one name string")
        name = self._string_arg(arg_exprs[0], "which")
        return CharValue(self.functions.which(name))

    def _builtin_show(self, arg_exprs: List[ast.Expr]) -> Array:
        if arg_exprs:
            raise EvalError("show/drawnow: expected no arguments")
        if self.plots is None:
            raise EvalError("show: no PlotSurface on this Session")
        show = getattr(self.plots, "show", None)
        if callable(show):
            show()
        return self.numerics.from_scalar(1.0)

    def _builtin_run(self, arg_exprs: List[ast.Expr]) -> Array:
        from pathlib import Path

        from openmatlab.lang.ast_nodes import FunctionDef
        from openmatlab.runtime.functions import Script, eval_script, load_mfile

        if len(arg_exprs) != 1:
            raise EvalError("run: expected one string path")
        name = self._string_arg(arg_exprs[0], "run")
        path = Path(name).expanduser()
        if not path.is_file():
            # try ToolboxPath by stem / name
            hit = None
            if self.functions.path is not None:
                hit = self.functions.path.find_mfile(name)
            if hit is None:
                raise EvalError(f"run: file not found: {name}")
            path = hit
        try:
            loaded = load_mfile(path)
        except ValueError as exc:
            raise EvalError(str(exc)) from exc
        if isinstance(loaded, FunctionDef):
            raise EvalError(
                f"run: {path} is a function file; call it as a function instead"
            )
        assert isinstance(loaded, Script)
        eval_script(loaded, self)
        return self.numerics.from_scalar(1.0)

    def _eval_binop(self, expr: ast.BinOp) -> Value:
        from openmatlab.runtime.char_value import CharValue
        import numpy as np
        from openmatlab.numerics.ndarray_value import NDArrayValue

        op = expr.op
        if op in ("&&", "||"):
            return self._eval_short_circuit(expr)
        lv = self.eval_expr(expr.left)
        rv = self.eval_expr(expr.right)

        def _as_numeric(v: Value, side: str) -> Array:
            if isinstance(v, CharValue):
                codes = [float(ord(ch)) for ch in v.text]
                if not codes:
                    return NDArrayValue(np.zeros((1, 0), dtype=np.float64))
                return NDArrayValue(np.asarray(codes, dtype=np.float64).reshape(1, -1))
            return self._require_array(v, f"binop:{side}")

        # char + char → concat for + only
        if op == "+" and isinstance(lv, CharValue) and isinstance(rv, CharValue):
            return CharValue(lv.text + rv.text)  # type: ignore[return-value]
        left = _as_numeric(lv, "left")
        right = _as_numeric(rv, "right")
        n = self.numerics
        if op == "+":
            return n.add(left, right)
        if op == "-":
            return n.sub(left, right)
        if op == "*":
            return n.matmul(left, right)
        if op == "/":
            return n.elem_div(left, right)
        if op == ".*":
            return n.elem_mul(left, right)
        if op == "./":
            return n.elem_div(left, right)
        if op in (".^", "^"):
            try:
                return n.power(left, right, elementwise=(op == ".^"))
            except Exception as exc:
                msg = str(exc)
                raise EvalError(
                    msg if ("power" in msg.lower()) else f"power: {msg}"
                ) from exc
        if op in ("<", "<=", ">", ">=", "==", "~="):
            return self._eval_relational(op, left, right)
        if op in ("&", "|"):
            a, b = self._bool_buf(left), self._bool_buf(right)
            try:
                return self._logical(a & b if op == "&" else a | b)
            except ValueError as exc:
                raise EvalError(f"{op}: matrix dimensions must agree") from exc
        raise EvalError(f"Unknown binary op: {op}")

    def _bool_buf(self, v: Value):
        """Logical view of a numeric/logical array (NaN is an error, as in MATLAB)."""
        import numpy as np

        arr = self._require_array(v, "logical")
        buf = np.asarray(arr.backend_buffer())
        if buf.dtype != np.bool_ and np.any(np.isnan(buf)):
            raise EvalError("NaN's cannot be converted to logicals.")
        return buf.astype(bool)

    def _logical(self, buf) -> Array:
        import numpy as np
        from openmatlab.numerics.ndarray_value import NDArrayValue

        buf = np.asarray(buf, dtype=bool)
        return NDArrayValue(buf.reshape((1, 1)) if buf.ndim == 0 else buf)

    def _eval_short_circuit(self, expr: ast.BinOp) -> Array:
        def scalar(side: ast.Expr) -> bool:
            b = self._bool_buf(self.eval_expr(side))
            if b.size != 1:
                raise EvalError(
                    f"Operands to the {expr.op} operator must be convertible to "
                    "logical scalar values."
                )
            return bool(b.reshape(-1)[0])

        left = scalar(expr.left)
        if (expr.op == "&&" and not left) or (expr.op == "||" and left):
            return self._logical(left)
        return self._logical(scalar(expr.right))

    def _eval_matrix(self, expr: ast.MatrixLiteral) -> Value:
        """[a b; c d]: horzcat each row, then vertcat rows (MATLAB rules).

        Numeric/logical arrays concatenate when dims agree ([] is skipped);
        all-logical stays logical. Any cell element makes a cell result (other
        elements wrap as 1x1 cells). Char rows concatenate as text (numbers
        convert by code).
        """
        from openmatlab.runtime.cell_value import CellValue
        from openmatlab.runtime.char_value import CharValue

        rows = [self._matrix_row_values(row) for row in expr.rows]
        flat = [v for r in rows for v in r]
        if any(isinstance(v, CellValue) for v in flat):
            return self._concat_cells(rows)
        if any(isinstance(v, CharValue) for v in flat):
            return self._concat_chars(rows)
        return self._concat_arrays(rows)

    def _matrix_row_values(self, row) -> list:
        from openmatlab.runtime.cell_value import CellValue

        out: list = []
        for el in row:
            val = self.eval_expr(el)
            # CSL inside []: [c{:}] expands contents into the row
            if (
                isinstance(el, ast.CellIndexExpr)
                and all(self._is_bare_colon(ix) for ix in el.indices)
                and isinstance(val, CellValue)
            ):
                rr, cc = val.shape
                out.extend(val.get(i, j) for j in range(cc) for i in range(rr))
                continue
            out.append(val)
        return out

    _CONCAT_ERR = "Dimensions of arrays being concatenated are not consistent."

    def _concat_arrays(self, rows: list) -> Array:
        import numpy as np
        from openmatlab.numerics.ndarray_value import NDArrayValue

        bufs = []
        for r in rows:
            parts = []
            for v in r:
                b = np.asarray(self._require_array(v, "matrix").backend_buffer())
                b = b.reshape(1, 1) if b.ndim == 0 else (b.reshape(1, -1) if b.ndim == 1 else b)
                if b.shape != (0, 0):  # [] is ignored in concatenation
                    parts.append(b)
            if not parts:
                continue
            if len({p.shape[0] for p in parts}) != 1:
                raise EvalError(self._CONCAT_ERR)
            bufs.append(np.concatenate(parts, axis=1) if len(parts) > 1 else parts[0])
        if not bufs:
            return self.numerics.from_nested([])
        if len({b.shape[1] for b in bufs}) != 1:
            raise EvalError(self._CONCAT_ERR)
        out = np.concatenate(bufs, axis=0) if len(bufs) > 1 else bufs[0]
        if out.dtype != np.bool_ and not np.iscomplexobj(out):
            out = out.astype(np.float64)
        return NDArrayValue(np.array(out))

    def _concat_cells(self, rows: list):
        from openmatlab.runtime.cell_value import CellValue

        grids = []
        for r in rows:
            parts = []
            for v in r:
                if not isinstance(v, CellValue):
                    if hasattr(v, "numel") and v.numel() == 0 and v.shape == (0, 0):
                        continue  # [] ignored
                    v = CellValue(rows=((v,),))
                if v.shape == (0, 0):
                    continue
                parts.append(v)
            if not parts:
                continue
            if len({p.shape[0] for p in parts}) != 1:
                raise EvalError(self._CONCAT_ERR)
            grids.append(
                [tuple(x for p in parts for x in p.rows[i]) for i in range(parts[0].shape[0])]
            )
        if not grids:
            return CellValue.empty(0, 0)
        if len({len(g[0]) for g in grids}) != 1:
            raise EvalError(self._CONCAT_ERR)
        return CellValue(rows=tuple(row for g in grids for row in g))

    def _concat_chars(self, rows: list):
        import numpy as np
        from openmatlab.runtime.char_value import CharValue

        texts = []
        for r in rows:
            t = ""
            for v in r:
                if isinstance(v, CharValue):
                    t += v.text
                    continue
                b = np.asarray(self._require_array(v, "matrix").backend_buffer())
                if b.ndim == 2 and min(b.shape) > 1:
                    raise EvalError(self._CONCAT_ERR)
                t += "".join(chr(int(x)) for x in b.reshape(-1))
            if t:
                texts.append(t)
        if len(texts) > 1:
            if len({len(t) for t in texts}) != 1:
                raise EvalError(self._CONCAT_ERR)
            raise EvalError("multi-row char matrices are not supported yet")
        return CharValue(texts[0] if texts else "")

    def _eval_colon(self, expr: ast.ColonExpr) -> Array:
        if expr.start is None or expr.stop is None:
            raise EvalError("Colon requires start and stop")
        start = self._as_float(
            self._require_array(self.eval_expr(expr.start), "colon")
        )
        stop = self._as_float(
            self._require_array(self.eval_expr(expr.stop), "colon")
        )
        step = 1.0
        if expr.step is not None:
            step = self._as_float(
                self._require_array(self.eval_expr(expr.step), "colon")
            )
        return self.numerics.colon(start, stop, step)

    def _as_float(self, val: Array) -> float:
        if not val.is_scalar():
            raise EvalError("Expected scalar")
        return float(val.backend_buffer().reshape(-1)[0])

    def _eval_relational(self, op: str, left: Array, right: Array) -> Array:
        import numpy as np
        from openmatlab.numerics.ndarray_value import NDArrayValue

        a = np.asarray(left.backend_buffer(), dtype=float)
        b = np.asarray(right.backend_buffer(), dtype=float)
        if op == "<":
            r = a < b
        elif op == "<=":
            r = a <= b
        elif op == ">":
            r = a > b
        elif op == ">=":
            r = a >= b
        elif op == "==":
            r = a == b
        elif op == "~=":
            r = a != b
        else:
            raise EvalError(f"Unknown relational op: {op}")
        r = np.asarray(r, dtype=bool)
        if r.ndim == 0:
            r = r.reshape(1, 1)
        elif r.ndim == 1:
            r = r.reshape(1, -1)
        return NDArrayValue(r)

    def _truthy(self, val: Value) -> bool:
        arr = self._require_array(val, "condition")
        if arr.numel() == 0:
            return False
        import numpy as np

        buf = np.asarray(arr.backend_buffer(), dtype=float).reshape(-1)
        return bool(np.all(buf != 0))


    def _values_equal(self, a: Value, b: Value) -> bool:
        """Scalar/char equality for switch/case matching."""
        from openmatlab.runtime.char_value import CharValue

        if isinstance(a, CharValue) or isinstance(b, CharValue):
            if not isinstance(a, CharValue) or not isinstance(b, CharValue):
                return False
            return a.text == b.text
        try:
            aa = self._require_array(a, "switch")
            bb = self._require_array(b, "switch")
        except EvalError:
            return False
        if aa.numel() != 1 or bb.numel() != 1:
            return False
        import numpy as np

        av = float(np.asarray(aa.backend_buffer(), dtype=float).reshape(-1)[0])
        bv = float(np.asarray(bb.backend_buffer(), dtype=float).reshape(-1)[0])
        if av != av and bv != bv:  # both NaN
            return True
        return av == bv

    def _eval_switch(self, stmt: ast.SwitchStmt) -> Value:
        needle = self.eval_expr(stmt.expr)
        last: Value = self.numerics.from_scalar(0.0)
        for case in stmt.cases:
            for vexpr in case.values:
                if self._values_equal(needle, self.eval_expr(vexpr)):
                    for s in case.body:
                        last = self.eval_stmt(s)
                    return last
        if stmt.otherwise is not None:
            for s in stmt.otherwise:
                last = self.eval_stmt(s)
        return last

    def _eval_if(self, stmt: ast.IfStmt) -> Value:
        last: Value = self.numerics.from_scalar(0.0)
        for branch in stmt.branches:
            if self._truthy(self.eval_expr(branch.condition)):
                for s in branch.body:
                    last = self.eval_stmt(s)
                return last
        if stmt.else_body is not None:
            for s in stmt.else_body:
                last = self.eval_stmt(s)
        return last

    def _eval_for(self, stmt: ast.ForStmt) -> Value:
        iterable = self._require_array(self.eval_expr(stmt.iterable), "for")
        import numpy as np

        vals = np.asarray(iterable.backend_buffer(), dtype=float).reshape(-1)
        last: Value = self.numerics.from_scalar(0.0)
        self._loop_depth += 1
        try:
            for x in vals:
                self.workspace.set(stmt.var, self.numerics.from_scalar(float(x)))
                try:
                    for s in stmt.body:
                        last = self.eval_stmt(s)
                except _ContinueSignal:
                    continue
                except _BreakSignal:
                    break
        finally:
            self._loop_depth -= 1
        return last

    def _eval_while(self, stmt: ast.WhileStmt) -> Value:
        last: Value = self.numerics.from_scalar(0.0)
        # Cap iterations to avoid hard hangs from user error in MVP
        self._loop_depth += 1
        try:
            for _ in range(1_000_000):
                if not self._truthy(self.eval_expr(stmt.condition)):
                    return last
                try:
                    for s in stmt.body:
                        last = self.eval_stmt(s)
                except _ContinueSignal:
                    continue
                except _BreakSignal:
                    return last
            raise EvalError("while: exceeded 1000000 iterations")
        finally:
            self._loop_depth -= 1

