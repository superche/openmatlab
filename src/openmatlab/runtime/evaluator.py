"""AST evaluator — Array-first on Session numerics (+ optional plot surface)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional, Sequence

from openmatlab.lang import ast_nodes as ast
from openmatlab.lang.parser import parse
from openmatlab.numerics.backend import ArrayBackend
from openmatlab.runtime import callstack as _callstack
from openmatlab.runtime import debugger as _debugger
from openmatlab.runtime.functions import FunctionResolver
from openmatlab.runtime.value import Array, Value
from openmatlab.runtime.workspace import Workspace

import numpy as _np
from openmatlab.numerics.ndarray_value import NDArrayValue as _NDArrayValue

_F64 = _np.dtype(_np.float64)

if TYPE_CHECKING:
    from openmatlab.host.plot_surface import PlotSurface


class EvalError(Exception):
    """User-visible MATLAB error; ``identifier`` is the MATLAB message id (Epic #530)."""

    def __init__(self, message: str = "", identifier: str = "") -> None:
        super().__init__(message)
        self.identifier = identifier


class _BreakSignal(Exception):
    """Internal: break leaves the innermost for/while."""


class _ContinueSignal(Exception):
    """Internal: continue skips to next iteration of innermost for/while."""


class _ReturnSignal(Exception):
    """Internal: return exits current function/script body."""


_AST_NUM, _AST_BINOP, _AST_NAME = ast.NumberLiteral, ast.BinOp, ast.Name
_AST_INDEX, _AST_CALL = ast.IndexExpr, ast.CallExpr
_SUBS_NODES = (ast.FieldExpr, ast.IndexExpr, ast.CallExpr, ast.CellIndexExpr)


def _is_class_obj(v) -> bool:
    return bool(getattr(v, "is_class_instance", False))


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
        self._no_output = None
        self._nargs = None  # (nargin, nargout) inside an .m function call (#531)
        self._persist_key = None
        self._frame = None  # callstack.Frame of the running M-file function/script (#698)

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
        from openmatlab.numerics.numpy_backend import NumericsError

        self._no_output = None
        fr = self._frame
        if fr is not None:
            fr.line = getattr(stmt, "_line", fr.line)
            if _debugger.ON:  # breakpoints / stepping (M11 D-E2); one global read otherwise
                d = _debugger.active()
                if d is not None:
                    d.on_statement(self, fr, stmt)
        try:
            value = self._exec_stmt(stmt)
        except (_BreakSignal, _ContinueSignal, _ReturnSignal):
            raise
        except NumericsError as exc:
            # backend errors are user errors (MATLAB message), not crashes
            err = EvalError(str(exc))
            _callstack.attach(err)
            if _debugger.ON and fr is not None:  # dbstop if error / caught error (M11 D-E3)
                _debugger.on_error(self, fr, err)
            raise err from exc
        except Exception as exc:
            _callstack.attach(exc)
            if _debugger.ON and fr is not None and isinstance(exc, EvalError):
                _debugger.on_error(self, fr, exc)
            raise
        if _debugger.ON and fr is not None:  # dbstop if naninf (M11 D-E3)
            _debugger.on_value(self, fr, value)
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
            names = tuple(n for n in stmt.names if n != "~")
        elif isinstance(stmt, ast.ChainAssign):
            from openmatlab.runtime import struct_eval as _se

            names = (_se._steps(stmt.target)[0],)
        elif isinstance(stmt, ast.ExprStmt):
            from openmatlab.runtime.struct_value import CsList

            if self._no_output is value:  # a call with no outputs shows nothing (MATLAB)
                return
            if isinstance(value, CsList):  # each value shows as ans (MATLAB)
                for v in value.values:
                    d.bind_ans(v)
                    if show:
                        self._show_value(d, v)
                return
            if isinstance(stmt.expr, ast.Name) and stmt.expr.id in self.workspace:
                if show:
                    self._show_value(d, value, name=stmt.expr.id)
                return
            d.bind_ans(value)
            if show:
                self._show_value(d, value)
            return
        else:
            return
        if show:
            for n in names:
                self._show_value(d, self.workspace.get(n), name=n)

    def _show_value(self, d, value, name=None):
        """Variable display; a class's display/disp overload takes over (O-E4)."""
        if _is_class_obj(value) and getattr(d, "stream", None) is not None:
            from openmatlab.runtime import classdef as _cd, frames as _frames
            from openmatlab.runtime.char_value import CharValue

            m = value.info.find_method("display")
            if m is not None:
                with _frames.calling(self):
                    m([value], nargout=0)
                return
            m = value.info.find_method("disp")
            if m is not None:
                fp = self.functions.resolve("fprintf")
                fp([CharValue("%s =\n\n"), CharValue(name or "ans")], nargout=0)
                with _frames.calling(self):
                    m([value], nargout=0)
                fp([CharValue("\n")], nargout=0)
                return
        d.show(value, name=name)

    def _exec_stmt(self, stmt: ast.Stmt) -> Value:
        if isinstance(stmt, (ast.ArrayAssign, ast.CellAssign, ast.ChainAssign)):  # subsasgn overloads (O-E4)
            from openmatlab.runtime import classdef_subs as _cs

            out = _cs.try_asgn(self, stmt.target, stmt.value)
            if out is not None:
                return out
        if isinstance(stmt, ast.Assign):
            value = self.eval_expr(stmt.value)
            self.workspace.set(stmt.name, value)
            return value
        if isinstance(stmt, ast.ChainAssign):  # s.a = v, s(2).b = v ... (Epic #506)
            from openmatlab.runtime import struct_eval as _se

            return _se.chain_assign(self, stmt)
        if isinstance(stmt, ast.CellAssign):
            return self._eval_cell_assign(stmt)
        if isinstance(stmt, ast.ArrayAssign):
            return self._graphics_array_assign(stmt)
        if isinstance(stmt, ast.MultiAssign):
            return self._eval_multi_assign(stmt)
        if isinstance(stmt, ast.IfStmt):
            return self._eval_if(stmt)
        if isinstance(stmt, ast.ForStmt):
            return self._eval_for(stmt)
        if isinstance(stmt, ast.WhileStmt):
            return self._eval_while(stmt)
        if isinstance(stmt, ast.TryStmt):
            return self._eval_try(stmt)
        if isinstance(stmt, ast.DeclStmt):
            from openmatlab.libs import function_intrinsics as _fi

            return _fi.declare(self, stmt)
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
            if isinstance(stmt.expr, ast.FieldExpr):  # s.f on a struct array is a cs-list
                from openmatlab.runtime import struct_eval as _se

                return _se.read_field(self, stmt.expr)
            ex = stmt.expr
            if isinstance(stmt, ast.CommandStmt) and self._name_bound(stmt.name):
                # `x -1` with a variable x is an expression, not a command (MATLAB)
                from openmatlab.lang.parser import parse as _parse

                last = self.numerics.from_scalar(0.0)
                for st in _parse(stmt.raw, commands=False):
                    last = self._exec_stmt(st)
                return last
            tgt = ex if isinstance(ex, ast.Name) else getattr(ex, "func", getattr(ex, "target", None))
            if (
                isinstance(ex, (ast.Name, ast.CallExpr, ast.IndexExpr))
                and isinstance(tgt, ast.Name)
                and not self._name_bound(tgt.id)
            ):
                from openmatlab.libs import function_intrinsics as _fi
                from openmatlab.libs import workspace_commands as _wc

                key = tgt.id.lower()
                fn0 = None
                from openmatlab.libs import math_builtins as _mb

                if key in _wc.STATEMENT_ZERO:
                    fn0 = _fi.INTRINSICS[key]
                elif key in _mb.STATEMENT_ZERO and key in getattr(self.functions, "builtins", {}):
                    _b = self.functions.builtins[key]
                    def fn0(_ev, a, n, _b=_b):  # builtins see the caller's resolver (M8 O-E5)
                        from openmatlab.runtime import frames as _frames

                        with _frames.calling(_ev):
                            return tuple(_b(a, nargout=0))
                elif isinstance(stmt, ast.CommandStmt) and key in _wc.COMMAND_ONLY:
                    fn0 = _wc.COMMAND_ONLY[key]
                if fn0 is not None:  # statement form: prints, no ans (#531/#532)
                    a = [] if isinstance(ex, ast.Name) else list(ex.args if isinstance(ex, ast.CallExpr) else ex.indices)
                    outs = fn0(self, self._eval_call_args(a), 0)
                    self._no_output = self.numerics.from_nested([])
                    return outs[0] if outs else self._no_output
            if isinstance(ex, (ast.CallExpr, ast.IndexExpr)):
                tgt = getattr(ex, "func", getattr(ex, "target", None))
                if isinstance(tgt, ast.Name) and not self._name_bound(tgt.id):
                    from openmatlab.runtime.functions import MFileCallable

                    try:
                        fn = self.functions.resolve(tgt.id)
                    except Exception:
                        fn = None
                    if isinstance(fn, MFileCallable):  # statement call: nargout == 0 (MATLAB)
                        args = self._eval_call_args(list(ex.args if isinstance(ex, ast.CallExpr) else ex.indices))
                        from openmatlab.runtime import frames as _frames

                        with _frames.calling(self):
                            outs = list(fn(args, nargout=0))
                        if not outs:
                            self._no_output = self.numerics.from_nested([])
                            return self._no_output
                        return outs[0]
            return self.eval_expr(stmt.expr)
        if isinstance(stmt, ast.FunctionDef):
            raise EvalError(
                "function definitions are only valid in .m files on the path"
            )
        raise EvalError(f"Unknown statement: {type(stmt)!r}")

    def _intrinsic_callable(self, name):
        from openmatlab.libs import function_intrinsics as _fi

        f = _fi.INTRINSICS.get(name.lower()) if name == name.lower() else None
        if f is None:
            return None
        ev = self

        def call(args, nargout=1, _f=f):
            return tuple(_f(ev, list(args), nargout))
        return call

    def eval_expr(self, expr: ast.Expr) -> Value:
        t = type(expr)  # exact-type fast paths for the hottest nodes (#797)
        if t is _AST_NUM:
            return self.numerics.from_scalar(expr.value)
        if t is _AST_BINOP:
            return self._eval_binop(expr)
        if t is _AST_NAME:
            try:
                return self.workspace.get(expr.id)
            except KeyError:
                pass  # unbound: the general path below resolves i/j, scripts and functions
        if t is _AST_INDEX or t is _AST_CALL:
            r = self._fast_scalar_index(expr)
            if r is not None:
                return r
        if isinstance(expr, _SUBS_NODES):  # subsref overloads (O-E4)
            from openmatlab.runtime import classdef_subs as _cs

            r = _cs.try_ref(self, expr)
            if r is not None:
                if not r:
                    self._no_output = self.numerics.from_nested([])
                    return self._no_output
                return r[0]
        if isinstance(expr, ast.FuncHandleExpr):
            from openmatlab.runtime.function_handle import FunctionHandleValue
            name = expr.name
            try:
                fn = self.functions.resolve(name)
            except Exception as e:
                fn = self._dotted_callable(name) if "." in name else None
                if fn is None and "." not in name:
                    fn = self._intrinsic_callable(name)  # @ishandle, @isvarname, @findobj ... (#766)
                if fn is None and not ("." not in name and name.lower() in
                                       getattr(self.functions, "_om_method_names", ())):
                    raise EvalError(f"function handle: undefined function '{name}'") from e
            if "." not in name and getattr(self.functions, "_om_method_names", None):
                fn = self._dispatching_handle_fn(name, fn)  # @method dispatches on argument class (#766)
            return FunctionHandleValue(name=name, fn=fn)
        if isinstance(expr, ast.AnonFuncExpr):
            return self._make_anon(expr)
        if isinstance(expr, ast.EndExpr):
            if not self._end_stack:
                raise EvalError("end outside of an indexing expression")
            return self.numerics.from_scalar(self._end_stack[-1])
        if isinstance(expr, ast.NumberLiteral):
            return self.numerics.from_scalar(expr.value)
        if isinstance(expr, ast.StringLiteral):
            from openmatlab.runtime.char_value import CharValue, StringValue

            return StringValue(expr.value) if expr.is_string else CharValue(expr.value)
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
                    try:
                        loaded = load_mfile(mfile)
                    except ValueError as exc:  # malformed file: MATLAB-style error (#529)
                        raise EvalError(str(exc)) from None
                    if isinstance(loaded, Script):
                        eval_script(loaded, self)
                        self._no_output = self.numerics.from_nested([])  # a script shows no ans (MATLAB)
                        return self._no_output
                    # else fall through to function resolve via _invoke_call
                # MATLAB: unbound name may be a zero-arg function/builtin (NaN, pi, …)
                try:
                    results = self._invoke_call(expr, [], nargout=1)
                except (EvalError, ValueError, LookupError):
                    if self._callable_name(expr.id):
                        raise  # a real function failed: keep its MATLAB error (#534)
                    results = None
                if results is not None:
                    if not results:
                        self._no_output = self.numerics.from_nested([])
                        return self._no_output
                    return results[0]
                raise EvalError(f"Undefined variable: {expr.id}")
        if isinstance(expr, ast.UnaryOp):
            v = self.eval_expr(expr.operand)
            if _is_class_obj(v):  # uminus/uplus/not overloads (O-E4)
                return self._overload_or_fail({"-": "uminus", "+": "uplus", "~": "not"}[expr.op], [v], expr.op)
            v = self._require_array(v, "unary")
            if expr.op == "+":
                return v
            if expr.op == "-":
                from openmatlab.numerics import sparse as _sp

                if _sp.is_sparse(v):  # -S stays sparse (#451), natively (#516)
                    return _sp.SparseValue(v.store.neg())
                z = self.numerics.from_scalar(0.0)
                return self.numerics.sub(z, v)
            if expr.op == "~":
                from openmatlab.numerics import sparse as _sp

                if _sp.is_sparse(v):  # ~S stays sparse (M3-E7 / #527)
                    nat = _sp.logical_not(v)
                    if nat is not None:
                        return nat
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
            from openmatlab.runtime.char_value import CharValue

            operand = self.eval_expr(expr.operand)
            if _is_class_obj(operand):  # ctranspose/transpose overloads (O-E4)
                return self._overload_or_fail("ctranspose" if expr.conjugate else "transpose", [operand],
                                              "'" if expr.conjugate else ".'")
            if getattr(operand, "is_struct", False):
                from openmatlab.runtime import struct_eval as _se

                return _se.transpose(operand)
            if hasattr(operand, "transpose_value"):  # categorical (M10 T-E2)
                return operand.transpose_value()
            if isinstance(operand, CharValue) and not getattr(operand, "is_string", False):
                return _codes_char(self.numerics.transpose(_char_codes(operand)))
            if getattr(operand, "is_string", False):
                from openmatlab.runtime import string_array as sa

                return sa.make(sa.to_grid(operand).T)  # (#459)
            from openmatlab.runtime.cell_value import CellValue

            if isinstance(operand, CellValue):  # cell transpose: c' == c.' (elements unchanged)
                if operand.nd:
                    raise EvalError("Transpose on ND array is not defined. Use PERMUTE instead.", "MATLAB:transpose:NDArray")
                return CellValue(rows=tuple(zip(*operand.rows)))
            out = self.numerics.transpose(
                self._require_array(operand, "transpose"),
                conjugate=expr.conjugate,
            )
            return operand.rewrap(out) if getattr(operand, "is_graphics_handle", False) else out  # (#768)
        if isinstance(expr, (ast.FieldExpr, ast.SuperRef, ast.MetaClassExpr)):  # classdef objects (M8)
            from openmatlab.runtime import classdef_eval as _cde

            r = _cde.call(self, expr, None if isinstance(expr, ast.FieldExpr) else [], 1)
            if r is not None:
                if not r:
                    self._no_output = self.numerics.from_nested([])
                    return self._no_output
                return r[0]
        if isinstance(expr, ast.FieldExpr):  # (Epic #506)
            from openmatlab.runtime import struct_eval as _se

            obj = self._object_field(expr)  # obj.Prop / containers.Map (Epic #539)
            if obj is not None:
                return obj

            return _se.single(_se.read_field(self, expr))
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
        from openmatlab.runtime import struct_eval as _se

        for row in expr.rows:
            vals = [v for cell in row for v in self._cs_values(cell)]
            if width is None:
                width = len(vals)
            elif len(vals) != width:
                raise EvalError("Cell literal rows must have equal length")
            rows.append(tuple(vals))
        return CellValue(rows=tuple(rows))



    def _eval_cell_index(self, expr: "ast.CellIndexExpr") -> Value:
        from openmatlab.runtime.cell_value import CellValue

        target = self.eval_expr(expr.target)
        if getattr(target, "is_string", False):  # s{k} is the char vector (#459)
            from openmatlab.runtime.char_value import CharValue

            picked = self._string_index(target, list(expr.indices))
            if picked.numel() != 1:
                raise EvalError("Brace indexing into a string array must select one element.")
            g = picked.text if not hasattr(picked, "data") else picked.data.flat[0]
            if g is None:
                raise EvalError("Unable to use a missing string as a character vector.")
            return CharValue(g)
        if not isinstance(target, CellValue):
            raise EvalError(
                f"cell index: expected cell, got {type(target).__name__}"
            )
        idxs = list(expr.indices)
        if len(idxs) > 2:  # N-D subscripts (#444, #479)
            res = self._cell_nd_select(target, idxs, "cell index")
            if res.size == 1:
                return res.flat[0]
            return CellValue(rows=tuple((v,) for v in res.reshape(-1, order="F")))
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


    def _graphics_array_assign(self, stmt: "ast.ArrayAssign") -> Value:
        """h(k) = g / h(k) = [] keep a graphics handle array a handle array (#768)."""
        t = stmt.target.target
        old = None
        if isinstance(t, ast.Name):
            try:
                old = self.workspace.get(t.id)
            except KeyError:
                old = None
        if not getattr(old, "is_graphics_handle", False):
            old = None  # hold no extra reference: lets x(k) = v store in place (#797)
            return self._eval_array_assign(stmt)
        out = self._eval_array_assign(stmt)
        new = self.workspace.get(t.id)
        if getattr(new, "is_graphics_handle", False):
            return out
        new2 = old.rewrap(new)
        if getattr(new2, "is_graphics_handle", False) and not all(i in old._model.objs or i != i for i in new2.ids):
            return out  # numbers that are not handles stay numbers
        if new2 is not new:
            self.workspace.set(t.id, new2)
        return new2 if out is new else out

    def _eval_array_assign(self, stmt: "ast.ArrayAssign") -> Value:
        from openmatlab.runtime.cell_value import CellValue

        target_expr = stmt.target.target
        if not isinstance(target_expr, ast.Name):
            raise EvalError("array assign: LHS must be name(...) in this MVP")
        name = target_expr.id
        rhs_val = self.eval_expr(stmt.value)
        try:
            arr = self.workspace.get(name)
        except KeyError:  # x(3) = v on an undefined x starts from [] (MATLAB, #508)
            import numpy as np
            from openmatlab.numerics.ndarray_value import NDArrayValue

            if isinstance(rhs_val, CellValue):
                arr = CellValue(rows=())
            elif getattr(rhs_val, "is_string", False):
                from openmatlab.runtime.string_array import StringArray

                arr = StringArray(np.empty((0, 0), dtype=object))
            else:
                arr = NDArrayValue(np.zeros((0, 0)))
        if _is_class_obj(rhs_val) and isinstance(arr, Array) and not getattr(arr, "is_object", False) \
                and not getattr(arr, "is_struct", False) and arr.numel() == 0:  # x = []; x(k) = obj (#766)
            from openmatlab.runtime import object_array as _oa

            arr = _oa.empty(rhs_val.info)
        if getattr(arr, "is_object", False):  # m(key) = v; handles mutate in place (Epic #539)
            out = arr.assign(self._object_index_args(arr, stmt.target.indices), rhs_val)
            self.workspace.set(name, out)
            return out
        if getattr(rhs_val, "is_missing_value", False):  # x(i) = missing (#504)
            from openmatlab.runtime import missing_value as _mv

            rhs_val = _mv.as_string() if getattr(arr, "is_string", False) else _mv.as_nan()
        if getattr(arr, "is_struct", False) or (
            getattr(rhs_val, "is_struct", False) and isinstance(arr, Array) and arr.numel() == 0
        ):  # s(i) = t / s(i) = [] (Epic #506)
            from openmatlab.runtime import struct_eval as _se

            cur = arr if getattr(arr, "is_struct", False) else None
            self.workspace.set(name, _se.struct_paren_assign(self, cur, list(stmt.target.indices), rhs_val))
            return rhs_val
        # c(i)=[] delete on cell arrays
        if isinstance(arr, CellValue):
            return self._eval_cell_paren_delete_or_assign(
                name, arr, list(stmt.target.indices), rhs_val
            )
        from openmatlab.runtime.char_value import CharValue

        is_char = isinstance(arr, CharValue) and not getattr(arr, "is_string", False)
        if getattr(arr, "is_string", False):
            return self._string_assign(name, arr, list(stmt.target.indices), rhs_val)
        arr_a = _char_codes(arr) if is_char else self._require_array(arr, "array assign")
        idxs = self._eval_subscripts(
            arr_a, list(stmt.target.indices), label="array assign"
        )
        if isinstance(rhs_val, CharValue) and not getattr(rhs_val, "is_string", False):
            rhs = _char_codes(rhs_val)
        else:
            rhs = self._require_array(rhs_val, "array assign")
        if len(idxs) > 1 and rhs.numel() > 0:
            idxs = self._fill_empty_colons(list(stmt.target.indices), idxs, rhs)
        if not is_char and arr_a is arr and _inplace_scalar_assign(self.workspace, name, arr, idxs, rhs):
            return rhs
        try:
            new_arr = self.numerics.set_index(arr_a, idxs, rhs)
        except Exception as exc:  # NumericsError
            raise EvalError(f"array assign: {exc}") from exc
        ix = stmt.target.indices
        if len(ix) == 1 and self._is_bare_colon(ix[0]) and rhs.numel() == 0:
            new_arr = self.numerics.from_nested([])  # A(:) = [] → 0x0 (MATLAB)
        if is_char:
            new_arr = _codes_char(new_arr)  # s(i) = 'x' keeps class char
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

        if len(idx_exprs) > 2:  # N-D paren assign / delete (#479)
            if isinstance(rhs_val, CellValue):
                self._cell_nd_store(name, cell, idx_exprs, rhs_val.to_obj(), "cell () assign")
                return rhs_val
            if isinstance(rhs_val, Array) and rhs_val.numel() == 0 and not getattr(rhs_val, "is_string", False):
                self._cell_nd_store(name, cell, idx_exprs, None, "cell () delete")
                return rhs_val
            raise EvalError(f"Conversion to cell from {rhs_val.matlab_class()} is not possible.")
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
                if rhs_val.numel() == 1:
                    # 1x1 cell RHS broadcasts to every selected position (MATLAB)
                    new_cell = cell
                    for i0, j0 in zip(ri, cj):
                        new_cell = new_cell.with_set(i0, j0, rhs_val.get(0, 0))
                    self.workspace.set(name, new_cell)
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
            if rhs_val.numel() == 1:
                new_cell = cell
                for j0 in cols_j:
                    for i0 in rows_i:
                        new_cell = new_cell.with_set(i0, j0, rhs_val.get(0, 0))
                self.workspace.set(name, new_cell)
                return rhs_val
            # MATLAB: shapes must agree once singleton dims are dropped
            lhs = [d for d in (len(rows_i), len(cols_j)) if d != 1]
            rhs = [d for d in rhs_val.shape if d != 1]
            if lhs != rhs:
                raise EvalError(
                    "Unable to perform assignment because the size of the left side is "
                    f"{len(rows_i)}-by-{len(cols_j)} and the size of the right side is "
                    f"{rhs_val.shape[0]}-by-{rhs_val.shape[1]}."
                )
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
        if len(idx_exprs) == 2:
            # MATLAB: only whole rows c(i,:)=[] or whole columns c(:,j)=[]
            ri, cj = self._cell_subscript_lists(cell, idx_exprs, "cell () delete")
            if sorted(set(ri)) == list(range(rows)):
                keep = [j for j in range(cols) if j not in set(cj)]
                new_rows = tuple(tuple(cell.get(i, j) for j in keep) for i in range(rows))
            elif sorted(set(cj)) == list(range(cols)):
                keep = [i for i in range(rows) if i not in set(ri)]
                new_rows = tuple(tuple(cell.get(i, j) for j in range(cols)) for i in keep)
            else:
                raise EvalError("A null assignment can have only one non-colon index.")
            self.workspace.set(name, CellValue(rows=new_rows))
            return rhs_val
        drop = set(self._cell_linear_delete_positions(cell, idx_exprs[0]))
        flat = [
            cell.get(i, j)
            for j in range(cols)
            for i in range(rows)
            if i + j * rows not in drop
        ]
        if cols == 1 and rows != 1:
            # column stays column (0x1 is not representable; empty → 0x0)
            new_cell = CellValue(rows=tuple((v,) for v in flat))
        else:
            # row vector or matrix → 1xN row (MATLAB linear delete)
            new_cell = CellValue(rows=(tuple(flat),))
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
        except KeyError:  # c{2} = v on an undefined c creates a cell (MATLAB, #508)
            cell = CellValue(rows=())
        if getattr(cell, "is_string", False):  # s{k} = 'x' (#459)
            return self._string_assign(name, cell, list(stmt.target.indices), self.eval_expr(stmt.value))
        if not isinstance(cell, CellValue):
            raise EvalError(
                f"cell assign: expected cell, got {type(cell).__name__}"
            )
        value = self.eval_expr(stmt.value)
        idxs = list(stmt.target.indices)
        if len(idxs) > 2:  # N-D content assign, grows (#444, #479)
            import numpy as np

            one = np.empty((1, 1), dtype=object)
            one[0, 0] = value
            self._cell_nd_store(name, cell, idxs, one, "cell assign")
            return value
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
        rows, cols = cell.shape  # an empty cell yields an empty cs-list (c{:} with c = {}, #766)

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
            raw = np.asarray(v.backend_buffer())
            limit = linear_numel if linear_numel is not None else dim_size
            if raw.dtype == np.bool_:  # logical mask (#766)
                m = raw.reshape(-1, order="F")
                if m.size > limit and m[limit:].any():
                    raise EvalError(f"{label}: index {int(np.flatnonzero(m)[-1]) + 1} exceeds {limit}")
                self._cell_idx_shape = (int(np.count_nonzero(m)), 1)
                return [int(k) for k in np.flatnonzero(m)]
            self._cell_idx_shape = tuple(int(d) for d in raw.shape) if raw.ndim == 2 else (raw.size, 1)
            buf = np.asarray(raw, dtype=np.float64).reshape(-1, order="F")
            if buf.size == 0:
                return []
            if np.any(buf != np.floor(buf)) or np.any(buf < 1):
                raise EvalError(f"{label}: indices must be positive integers")
            out = []
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

    def _cell_nd_positions(self, cell):
        import numpy as np
        from openmatlab.numerics.ndarray_value import NDArrayValue

        obj = cell.to_obj()
        pos = NDArrayValue(np.arange(1, obj.size + 1, dtype=np.float64).reshape(obj.shape, order="F"))
        return obj, pos

    def _cell_nd_select(self, cell, idx_exprs: list, label: str):
        """N-D cell subscripts via a position map on the numeric path (#479)."""
        import numpy as np

        obj, pos = self._cell_nd_positions(cell)
        idxs = self._eval_subscripts(pos, idx_exprs, label=label)
        try:
            out = np.asarray(self.numerics.index(pos, idxs).backend_buffer())
        except Exception as exc:
            raise EvalError(str(exc)) from exc
        flat = obj.reshape(-1, order="F")
        res = np.empty(out.shape, dtype=object)
        for ix in np.ndindex(*out.shape):
            res[ix] = flat[int(out[ix]) - 1]
        return res

    def _cell_nd_store(self, name: str, cell, idx_exprs: list, rhs_obj, label: str) -> None:
        """N-D cell assign (rhs_obj grid) or delete (None); growth fills [] (#479)."""
        import numpy as np
        from openmatlab.numerics.ndarray_value import NDArrayValue
        from openmatlab.runtime.cell_value import CellValue

        obj, pos = self._cell_nd_positions(cell)
        n = obj.size
        idxs = self._eval_subscripts(pos, idx_exprs, label=label)
        if rhs_obj is None:
            rhs = NDArrayValue(np.zeros((0, 0)))
            rflat: list = []
        else:
            rhs = NDArrayValue(np.arange(n + 1, n + rhs_obj.size + 1, dtype=np.float64).reshape(rhs_obj.shape, order="F"))
            rflat = list(rhs_obj.reshape(-1, order="F"))
        try:
            new = np.asarray(self.numerics.set_index(pos, idxs, rhs).backend_buffer())
        except Exception as exc:
            raise EvalError(f"{label}: {exc}") from exc
        lookup = [None] + list(obj.reshape(-1, order="F")) + rflat
        res = np.empty(new.shape, dtype=object)
        for ix in np.ndindex(*new.shape):
            v = lookup[int(new[ix])]
            res[ix] = v if v is not None else NDArrayValue(np.zeros((0, 0)))
        self.workspace.set(name, CellValue.from_obj(res))

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
                # MATLAB `end` per dim (#173): dims past ndims are 1; the last
                # subscript spans all trailing dims (folded view).
                shape = tuple(target.shape) + (1,) * max(0, n - len(target.shape))
                if i < n - 1:
                    end_val = float(shape[i])
                else:
                    tail = 1
                    for d in shape[i:]:
                        tail *= int(d)
                    end_val = float(tail)
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

    def _fill_empty_colons(self, ix_exprs: list, idxs: List[Array], rhs: Array) -> List[Array]:
        """A(:,j) = v on a dimension of extent 0: the colon takes its extent from the
        RHS (MATLAB: ``y(mask,:) = col`` with ``y`` undefined, ``x = zeros(1,0); x(1,:) = 1:4``)."""
        k = len(idxs)
        empty = [d for d in range(k) if self._is_bare_colon(ix_exprs[d]) and idxs[d].numel() == 0]
        if not empty:
            return idxs
        import numpy as _np

        counts = []
        for a in idxs:
            buf = _np.asarray(a.backend_buffer())
            counts.append(int(_np.count_nonzero(buf)) if buf.dtype == _np.bool_ else int(buf.size))
        if rhs.numel() == 1:
            ext = {d: 1 for d in empty}
        else:
            rs = [int(x) for x in rhs.shape]
            rs = (rs + [1] * k)[:k] if len(rs) <= k else rs[: k - 1] + [int(rhs.numel() // max(1, _prod(rs[: k - 1])))]
            if all(counts[d] == rs[d] for d in range(k) if d not in empty):
                ext = {d: rs[d] for d in empty}
            elif len(empty) == 1:
                others = _prod([counts[d] for d in range(k) if d != empty[0]])
                if others == 0 or rhs.numel() % others:
                    return idxs
                ext = {empty[0]: int(rhs.numel() // others)}
            else:
                return idxs
        out = list(idxs)
        for d, n in ext.items():
            if n > 0:
                out[d] = self.numerics.colon(1.0, float(n), 1.0)
        return out

    def _require_array(self, val: Value, ctx: str) -> Array:
        if not isinstance(val, Array):
            if getattr(val, "is_table", False):  # MATLAB: no such operator/function for tables (M10)
                raise EvalError(f"Undefined function '{ctx}' for input arguments of type 'table'.",
                                "MATLAB:UndefinedFunction")
            raise EvalError(f"{ctx}: expected Array, got {type(val).__name__}")
        return val

    def _eval_multi_assign(self, stmt: ast.MultiAssign) -> Value:
        from openmatlab.runtime import struct_eval as _se

        if stmt.targets is not None:  # [s.f] = deal(...), [c{1:2}] = ... (#508)
            return _se.multi_assign_targets(self, stmt)
        nargout = len(stmt.names)
        if nargout < 1:
            raise EvalError("multi-assign: empty output list")
        expr = stmt.value
        if isinstance(expr, (ast.FieldExpr, ast.CellIndexExpr)):  # [a, b] = s.f / c{:} (#508)
            vals = _se.expand_rhs(self, expr)
            if len(vals) < nargout:
                raise EvalError("Insufficient number of outputs from right hand side of equal sign to satisfy assignment.")
            for name, val in zip(stmt.names, vals):
                if name != "~":
                    self.workspace.set(name, val)
            return vals[0]
        if isinstance(expr, ast.IndexExpr):
            target_expr, arg_exprs = expr.target, list(expr.indices)
        elif isinstance(expr, ast.Name):  # [a, b] = f with no parentheses
            target_expr, arg_exprs = expr, []
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
            if name != "~":  # [~, i] = f(...) discards that output
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
            body = expr.body
            if nargout > 1 and isinstance(body, (ast.IndexExpr, ast.CallExpr)):  # [a, b] = anon(x) (#766)
                t, a = (body.target, list(body.indices)) if isinstance(body, ast.IndexExpr) else \
                    (body.func, list(body.args))
                outs = ev._invoke_call(t, a, nargout=nargout)
                if outs is not None:
                    return tuple(outs)
            return (ev.eval_expr(body),)

        return FunctionHandleValue(name=expr.text, fn=call)

    @staticmethod
    def _is_bare_colon(expr: ast.Expr) -> bool:
        return isinstance(expr, ast.ColonExpr) and expr.start is None and expr.stop is None

    def _object_index_args(self, obj, arg_exprs) -> list:
        """obj(args): a bare ':' becomes the text ':'; 'end' resolves against the object's size (array-like only)."""
        import math

        from openmatlab.runtime.char_value import CharValue

        shape = tuple(obj.shape) if hasattr(obj, "shape") and hasattr(obj, "numel") else None
        out = []
        n = len(arg_exprs)
        for k, a in enumerate(arg_exprs):
            if self._is_bare_colon(a):
                out.append(CharValue(":"))
                continue
            if shape is None or getattr(obj, "is_handle", False) or obj.matlab_class() == "containers.Map":
                out.append(self.eval_expr(a))
                continue
            if n == 1:
                end = int(math.prod(shape))
            elif k < n - 1:
                end = shape[k] if k < len(shape) else 1
            else:
                end = int(math.prod(shape[k:])) if k < len(shape) else 1
            self._end_stack.append(float(end))
            try:
                out.append(self.eval_expr(a))
            finally:
                self._end_stack.pop()
        return out

    def _index_with_exprs(self, value, arg_exprs) -> Value:
        """value(arg_exprs...) for an already computed value (end and : resolve against it)."""
        Evaluator._tmp_seq += 1
        t = f"__om_ix{Evaluator._tmp_seq}"
        self.workspace.set(t, value)
        try:
            return self.eval_expr(ast.IndexExpr(target=ast.Name(t), indices=tuple(arg_exprs)))
        finally:
            self.workspace.clear(t)

    _tmp_seq = 0

    def _index_with_cs_args(self, target_expr, arg_exprs) -> Value:
        """x(i, c{:}): cs-lists in subscripts expand into separate subscripts (#766)."""
        names, new = [], []
        try:
            for a in arg_exprs:
                if not isinstance(a, ast.CellIndexExpr):
                    new.append(a)
                    continue
                for v in self._cs_values(a):
                    Evaluator._tmp_seq += 1
                    t = f"__om_cs{Evaluator._tmp_seq}"
                    self.workspace.set(t, v)
                    names.append(t)
                    new.append(ast.Name(t))
            return self._eval_call_or_index(target_expr, new)
        finally:
            for t in names:
                self.workspace.clear(t)

    def _fast_scalar_index(self, expr):
        """A(i) / A(i, j) on a plain numeric variable with bound-name or literal real
        scalar subscripts: skip overload, call-resolution and subscript machinery (#797).
        Returns None whenever any precondition fails, so the general path decides."""
        target = expr.target if type(expr) is _AST_INDEX else expr.func
        args = expr.indices if type(expr) is _AST_INDEX else expr.args
        if type(target) is not _AST_NAME or not 1 <= len(args) <= 2:
            return None
        get = self.workspace.get
        try:
            a = get(target.id)
        except KeyError:
            return None
        if type(a) is not _NDArrayValue:
            return None
        idx = []
        for e in args:
            te = type(e)
            if te is _AST_NAME:
                try:
                    v = get(e.id)
                except KeyError:
                    return None
                if type(v) is not _NDArrayValue:
                    return None
                b = v._data
                if b.size != 1 or b.dtype != _F64:
                    return None
                idx.append(v)
            elif te is _AST_NUM:
                idx.append(self.numerics.from_scalar(e.value))
            else:
                return None
        return self.numerics.index(a, idx)

    def _eval_call_or_index(self, target_expr: ast.Expr, arg_exprs: List[ast.Expr]) -> Value:
        if isinstance(target_expr, (ast.FieldExpr, ast.SuperRef)):  # classdef objects (M8)
            from openmatlab.runtime import classdef_eval as _cde

            r = _cde.call(self, target_expr, arg_exprs, 1)
            if r is not None:
                if not r:
                    self._no_output = self.numerics.from_nested([])
                    return self._no_output
                return r[0]
        if isinstance(target_expr, ast.FieldExpr):  # containers.Map(...), obj.method(...) (Epic #539)
            out = self._object_call(target_expr, arg_exprs)
            if out is not None:
                return out
        results = self._invoke_call(target_expr, arg_exprs, nargout=1)
        if results is None and any(isinstance(a, ast.CellIndexExpr) for a in arg_exprs):
            return self._index_with_cs_args(target_expr, arg_exprs)
        if results is None:
            target = self.eval_expr(target_expr)
            if getattr(target, "is_object", False):  # obj(args) (Epic #539)
                return target.index(self._object_index_args(target, arg_exprs))
            from openmatlab.runtime.cell_value import CellValue
            from openmatlab.runtime.function_handle import FunctionHandleValue

            if isinstance(target, CellValue):
                return self._eval_cell_paren_index(target, arg_exprs)
            if getattr(target, "is_struct", False):  # s(i) (Epic #506)
                from openmatlab.runtime import struct_eval as _se

                return _se.struct_index(self, target, arg_exprs)
            if isinstance(target, FunctionHandleValue):
                from openmatlab.runtime import frames as _frames

                with _frames.calling(self):
                    outs = target.call(self._eval_call_args(arg_exprs), nargout=1)
                if not outs:
                    raise EvalError("function handle call returned no value")
                return outs[0]
            from openmatlab.runtime.char_value import CharValue

            if getattr(target, "is_string", False):
                return self._string_index(target, arg_exprs)  # (#459)
            if isinstance(target, CharValue):
                # char indexing (#457): index the code matrix, convert back
                codes = _char_codes(target)
                idxs = self._eval_subscripts(codes, arg_exprs, label="index")
                out = self.numerics.index(codes, idxs)
                if len(arg_exprs) == 1 and self._is_bare_colon(arg_exprs[0]):
                    import numpy as np
                    from openmatlab.numerics.ndarray_value import NDArrayValue

                    out = NDArrayValue(np.asarray(out.backend_buffer()).reshape(-1, 1))
                return _codes_char(out)
            target_a = self._require_array(target, "index")
            if getattr(target_a, "issparse", False) and len(arg_exprs) == 1 and self._is_bare_colon(arg_exprs[0]):
                return type(target_a)(target_a.store.reshape(target_a.numel(), 1))  # S(:) without 1:numel (#523)
            idxs = self._eval_subscripts(target_a, arg_exprs, label="index")
            out = self.numerics.index(target_a, idxs)
            if len(arg_exprs) == 1 and self._is_bare_colon(arg_exprs[0]):
                # A(:) is always a numel×1 column (MATLAB), even for rows / empties
                import numpy as np
                from openmatlab.numerics.ndarray_value import NDArrayValue

                if getattr(out, "issparse", False):  # S(:) stays sparse (#517)
                    return type(out)(out.store.reshape(out.numel(), 1))
                out = NDArrayValue(np.asarray(out.backend_buffer()).reshape(-1, 1))
            if getattr(target_a, "is_graphics_handle", False):  # h(k) stays a handle array (#768)
                out = target_a.rewrap(out)
            return out
        if not results:
            self._no_output = self.numerics.from_nested([])
            return self._no_output
        return results[0]

    def _eval_cell_paren_index(
        self, cell: "object", arg_exprs: List[ast.Expr]
    ) -> Value:
        """c(i) / c(:,j) → sub-cell (paren slice, not content)."""
        from openmatlab.runtime.cell_value import CellValue

        assert isinstance(cell, CellValue)
        idxs = list(arg_exprs)
        if len(idxs) > 2:  # N-D subscripts (#444, #479)
            return CellValue.from_obj(self._cell_nd_select(cell, idxs, "cell () index"))
        if len(idxs) == 1:
            ri, cj = self._cell_subscript_lists(cell, idxs, "cell () index")
            # linear positions → column cell of 1×1 contents wrappers? MATLAB: c(1:2) is 1×2 or 2×1 subcell of cells
            # Each selected element stays as cell content inside the subarray
            # NOTE: MATLAB keeps a row cell's orientation here; changing it conflicts with
            # tests/unit/test_epic30_cells.py (reported to Shaw, #766)
            if len(ri) == 1:
                return CellValue(rows=((cell.get(ri[0], cj[0]),),))
            return CellValue(rows=tuple((cell.get(i, j),) for i, j in zip(ri, cj)))
        rows_i, cols_j = self._cell_subscript_lists(cell, idxs, "cell () index")
        grid = tuple(tuple(cell.get(i, j) for j in cols_j) for i in rows_i)
        return CellValue(rows=grid)


    def _cs_values(self, a) -> list:
        """Values of one list-context element: s.f and c{...} expand to their cs-list (#766)."""
        from openmatlab.runtime.cell_value import CellValue

        if isinstance(a, ast.FieldExpr):
            from openmatlab.runtime import struct_eval as _se

            return _se.expand(self, a)
        if isinstance(a, ast.CellIndexExpr):
            t = a.target
            if isinstance(t, ast.Name) and t.id in self.workspace:
                target = self.workspace.get(t.id)
            elif isinstance(t, (ast.Name, ast.CellIndexExpr)):
                target = None
            else:
                target = self.eval_expr(t)
            if isinstance(target, CellValue):
                idxs = list(a.indices)
                if len(idxs) > 2:
                    res = self._cell_nd_select(target, idxs, "cell index")
                    return list(res.reshape(-1, order="F"))
                if not idxs:
                    return [target]
                ri, cj = self._cell_subscript_lists(target, idxs, "cell index")
                if len(idxs) == 1:
                    return [target.get(i, j) for i, j in zip(ri, cj)]
                return [target.get(i, j) for j in cj for i in ri]
        return [self.eval_expr(a)]

    def _eval_call_args(self, arg_exprs: List[ast.Expr]) -> list:
        """Evaluate call args with cell CSL expansion c{:} / c{:,k} / s.f (#506, #766)."""
        out: list = []
        for a in arg_exprs:
            out.extend(self._cs_values(a))
        return out

    def _invoke_call(
        self,
        target_expr: ast.Expr,
        arg_exprs: List[ast.Expr],
        *,
        nargout: int,
    ):
        """Return output sequence for a function call, or None if indexing."""
        if isinstance(target_expr, (ast.FieldExpr, ast.SuperRef)):  # [a, b] = obj.m(...) (M8)
            from openmatlab.runtime import classdef_eval as _cde

            r = _cde.call(self, target_expr, arg_exprs, nargout)
            if r is not None:
                return r
        if not (
            isinstance(target_expr, ast.Name)
            and not self._name_bound(target_expr.id)
        ):
            if nargout != 1:
                from openmatlab.runtime.function_handle import FunctionHandleValue

                if isinstance(target_expr, ast.Name):
                    h = self.workspace.get(target_expr.id)
                elif isinstance(target_expr, ast.FieldExpr):  # [a, b] = s.fn(x)
                    from openmatlab.runtime import struct_eval as _se

                    h = _se.single(_se.read_field(self, target_expr))
                else:
                    h = None
                if isinstance(h, FunctionHandleValue):  # [a, b] = h(x) (#766)
                    from openmatlab.runtime import frames as _frames

                    with _frames.calling(self):
                        return list(h.call(self._eval_call_args(arg_exprs), nargout=nargout))
                raise EvalError("multi-assign RHS must be a function call")
            return None
        n = target_expr.id
        key = n.lower()
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
        from openmatlab.libs import function_intrinsics as _fi
        from openmatlab.runtime import classdef as _cd
        from openmatlab.runtime import frames as _frames

        args = None
        if key in _cd.method_names(self.functions):  # f(obj, ...) runs obj's method f first (MATLAB precedence, M8)
            try:
                args = self._eval_call_args(arg_exprs)
            except EvalError:
                if not self._callable_name(n):
                    raise EvalError(f"Undefined function or variable: {n}") from None
                raise
            m = _cd.find_method_for_args(n, args)
            if m is not None:
                with _frames.calling(self):
                    return list(m(args, nargout=nargout))
        if key in _fi.INTRINSICS:  # need the caller's frame (#531)
            if args is None:
                args = self._eval_call_args(arg_exprs)
                m = _cd.find_method_for_args(n, args)  # class loaded while evaluating the arguments
                if m is not None:
                    with _frames.calling(self):
                        return list(m(args, nargout=nargout))
            return _fi.INTRINSICS[key](self, args, nargout)
        try:
            fn = self.functions.resolve(n)
        except LookupError as exc:
            if args is None and arg_exprs:  # maybe a method of a class the arguments load (M8)
                try:
                    args = self._eval_call_args(arg_exprs)
                except EvalError:
                    raise EvalError(str(exc)) from exc
                m = _cd.find_method_for_args(n, args)
                if m is not None:
                    with _frames.calling(self):
                        return list(m(args, nargout=nargout))
            raise EvalError(str(exc)) from exc
        if args is None:
            args = self._eval_call_args(arg_exprs)
            m = _cd.find_method_for_args(n, args) if any(_cd.dispatchable(a) for a in args) else None
            if m is not None:
                with _frames.calling(self):
                    return list(m(args, nargout=nargout))

        self._call_arg_exprs = arg_exprs  # for inputname in the callee (#569)
        try:
            with _frames.calling(self):  # callee sees this frame as its caller (evalin/assignin)
                results = list(fn(args, nargout=nargout))
        except ValueError as exc:  # builtin argument errors (e.g. BuiltinError)
            msg = str(exc)
            raise EvalError(msg if msg.startswith(f"{n}:") else f"{n}: {msg}") from exc
        except (IndexError, TypeError, KeyError, AttributeError, ZeroDivisionError) as exc:
            # a builtin hit bad arguments it does not validate: never leak a Python error (#606)
            if not args:
                raise EvalError("Not enough input arguments.", "MATLAB:minrhs") from exc
            raise EvalError(f"Error using {n}: invalid input arguments.", f"MATLAB:{n}:invalidInput") from exc
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

    def _callable_name(self, name: str) -> bool:
        from openmatlab.libs import function_intrinsics as _fi

        if name.lower() in _fi.INTRINSICS:
            return True
        try:
            self.functions.resolve(name)
            return True
        except Exception:
            return False

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
        self._no_output = self.numerics.from_nested([])  # run(...) shows no ans (MATLAB)
        return self._no_output

    # ---------------------------------------------------------- objects (Epic #539)
    _OBJECT_METHODS = {"keys", "values", "iskey", "remove", "length", "isempty"}

    _OP_METHODS = {"+": "plus", "-": "minus", "*": "mtimes", ".*": "times", "/": "mrdivide", "./": "rdivide",
                   "\\": "mldivide", ".\\": "ldivide", "^": "mpower", ".^": "power", "==": "eq", "~=": "ne",
                   "<": "lt", "<=": "le", ">": "gt", ">=": "ge", "&": "and", "|": "or"}

    def _dotted_callable(self, name):
        """@Class.staticMethod -> a callable (M8)."""
        from openmatlab.runtime import classdef as _cd

        cls, _, meth = name.rpartition(".")
        try:
            ctor = self.functions.resolve(cls)
        except Exception:
            return None
        info = getattr(ctor, "info", None)
        if not isinstance(ctor, _cd.ClassConstructor) or info is None:
            return None
        m = info.find_method(meth)
        return m if m is not None and m.static else None

    def _dispatching_handle_fn(self, name, fn):
        from openmatlab.runtime import classdef as _cd, frames as _frames

        ev = self

        def call(args, *, nargout=1, **kw):
            m = _cd.find_method_for_args(name, list(args)) if any(_is_class_obj(a) for a in args) else None
            if m is not None:
                with _frames.calling(ev):
                    return m(list(args), nargout=nargout)
            if fn is None:
                raise EvalError(f"Undefined function '{name}' for input arguments of type "
                                f"'{args[0].matlab_class() if args else 'double'}'.", "MATLAB:UndefinedFunction")
            return fn(args, nargout=nargout, **kw)

        call.__wrapped__ = fn
        return call

    def _overload(self, name, args, nargout=1):
        """Call a class method overload ``name(args...)`` if any argument's class defines it (O-E4)."""
        from openmatlab.runtime import classdef as _cd, frames as _frames

        m = _cd.find_method_for_args(name, args)
        if m is None:
            return NotImplemented
        with _frames.calling(self):
            outs = list(m(list(args), nargout=nargout))
        if not outs:
            self._no_output = self.numerics.from_nested([])
            return self._no_output
        return outs[0]

    def _overload_or_fail(self, name, args, op):
        out = self._overload(name, args)
        if out is NotImplemented:
            cls = args[0].matlab_class()
            raise EvalError(f"Operator '{op}' is not supported for operands of type '{cls}'.", "MATLAB:UndefinedFunction")
        return out

    def _object_binop(self, op, lv, rv):
        if _is_class_obj(lv) or _is_class_obj(rv):  # operator overloading (O-E4)
            name = self._OP_METHODS.get(op)
            if name is not None:
                out = self._overload(name, [lv, rv])
                if out is not NotImplemented:
                    return out
        if getattr(lv, "is_object", False):
            out = lv.binop(op, rv, False)
            if out is not NotImplemented:
                return out
        if getattr(rv, "is_object", False):
            out = rv.binop(op, lv, True)
            if out is not NotImplemented:
                return out
        raise EvalError(f"Operator '{op}' is not supported for operands of type "
                        f"'{lv.matlab_class()}' and '{rv.matlab_class()}'.", "MATLAB:UndefinedFunction")

    def _object_base(self, expr):
        if isinstance(expr.target, ast.Name) and expr.name is not None:
            if expr.target.id == "containers" and not self._name_bound("containers"):
                return "containers"
            try:
                v = self.workspace.get(expr.target.id)
            except KeyError:
                return None
            return v if (getattr(v, "is_object", False) or getattr(v, "is_graphics_handle", False)) else None
        return None

    def _object_field(self, expr):
        base = self._object_base(expr)
        if base is None:
            return None
        if base == "containers":
            return self._object_call(expr, [])
        if expr.name.lower() in self._OBJECT_METHODS or (hasattr(base, "has_method") and base.has_method(expr.name)):
            return self._object_call(expr, [])
        return base.get_prop(expr.name)

    def _object_call(self, expr, arg_exprs):
        base = self._object_base(expr)
        if base is None:
            return None
        args = self._eval_call_args(arg_exprs)
        if base == "containers":
            if expr.name != "Map":
                raise EvalError(f"Undefined function or variable: containers.{expr.name}")
            fn, args = self.functions.resolve("containers.Map"), args
        elif hasattr(base, "call_method") and base.has_method(expr.name):  # inputParser ... (#569)
            with __import__("openmatlab.runtime.frames", fromlist=["calling"]).calling(self):
                outs = list(base.call_method(expr.name, args, 1))
            if not outs:
                self._no_output = self.numerics.from_nested([])
                return self._no_output
            return outs[0]
        else:
            if expr.name.lower() not in self._OBJECT_METHODS:
                if arg_exprs and getattr(base, "is_graphics_handle", False):  # ax.XLim(2) (O-E6)
                    return self._index_with_exprs(base.get_prop(expr.name), arg_exprs)
                if arg_exprs:
                    raise EvalError(f"Unrecognized method '{expr.name}' for class '{base.matlab_class()}'.", "MATLAB:noSuchMethodOrField")
                return base.get_prop(expr.name)
            fn, args = self.functions.resolve(expr.name), [base] + list(args)
        try:
            from openmatlab.runtime import frames as _frames

            with _frames.calling(self):
                outs = list(fn(args, nargout=1))
        except ValueError as exc:
            raise EvalError(str(exc)) from exc
        return outs[0] if outs else self.numerics.from_nested([])

    def _eval_binop(self, expr: ast.BinOp) -> Value:
        from openmatlab.runtime.char_value import CharValue
        import numpy as np
        from openmatlab.numerics.ndarray_value import NDArrayValue

        op = expr.op
        if op in ("&&", "||"):
            return self._eval_short_circuit(expr)
        lv = self.eval_expr(expr.left)
        rv = self.eval_expr(expr.right)
        if type(lv) is NDArrayValue and type(rv) is NDArrayValue and op in _FAST_SCALAR_OPS:
            r = _fast_scalar_binop(op, lv._data, rv._data)
            if r is not None:
                return r
        if getattr(lv, "is_object", False) or getattr(rv, "is_object", False):  # (Epic #539)
            return self._object_binop(op, lv, rv)

        def _as_numeric(v: Value, side: str) -> Array:
            if isinstance(v, CharValue):
                return _char_codes(v)
            return self._require_array(v, f"binop:{side}")

        if getattr(lv, "is_string", False) or getattr(rv, "is_string", False):
            return self._string_binop(op, lv, rv)
        left = _as_numeric(lv, "left")
        right = _as_numeric(rv, "right")
        n = self.numerics
        if op == "+":
            return n.add(left, right)
        if op == "-":
            return n.sub(left, right)
        if op == "*":
            return n.matmul(left, right)
        if op in ("/", "\\"):
            if op == "/" and (left.numel() == 1 or right.numel() == 1) and right.numel() == 1:
                return n.elem_div(left, right)
            if op == "\\" and left.numel() == 1:
                return n.elem_div(right, left)
            from openmatlab.libs.linalg_builtins import solve  # mldivide/mrdivide (#496)

            try:
                return solve("mrdivide" if op == "/" else "mldivide", left, right)
            except Exception as exc:
                raise EvalError(str(exc)) from exc
        if op == ".\\":
            return n.elem_div(right, left)
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

    def _string_binop(self, op: str, lv: Value, rv: Value) -> Value:
        """string scalar ops (#78): + concatenates, comparisons are textual."""
        from openmatlab.runtime.char_value import StringValue
        from openmatlab.runtime.string_array import StringArray

        if isinstance(lv, StringArray) or isinstance(rv, StringArray):
            return self._string_array_binop(op, lv, rv)
        a, b = _string_text(lv), _string_text(rv)
        if a is None or b is None:
            raise EvalError(f"Operator '{op}' is not supported for operands of type 'string'.")
        if op == "+":
            return StringValue(a + b)
        cmp = {"==": a == b, "~=": a != b, "<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}
        if op in cmp:
            return self._logical(np_bool(cmp[op]))
        raise EvalError(f"Operator '{op}' is not supported for operands of type 'string'.")

    def _string_array_binop(self, op: str, lv: Value, rv: Value) -> Value:
        """Elementwise string-array + and comparisons with scalar expansion (#459).
        <missing> propagates through +; it compares unequal to everything."""
        import numpy as np
        from openmatlab.runtime import string_array as sa

        ga, gb = sa.to_grid(lv), sa.to_grid(rv)
        bad = EvalError(f"Operator '{op}' is not supported for operands of type 'string'.")
        if ga is None or gb is None or op not in ("+", "==", "~=", "<", "<=", ">", ">="):
            raise bad
        if not (ga.size == 1 or gb.size == 1 or ga.shape == gb.shape):
            raise EvalError("Arrays have incompatible sizes for this operation.")
        a, b = np.broadcast_arrays(ga, gb)
        if op == "+":
            out = np.empty(a.shape, dtype=object)
            for ix in np.ndindex(*a.shape):
                x, y = a[ix], b[ix]
                out[ix] = None if x is None or y is None else x + y
            return sa.make(out)
        fns = {"==": lambda x, y: x == y, "~=": lambda x, y: x != y, "<": lambda x, y: x < y,
               "<=": lambda x, y: x <= y, ">": lambda x, y: x > y, ">=": lambda x, y: x >= y}
        res = np.zeros(a.shape, dtype=bool)
        for ix in np.ndindex(*a.shape):
            x, y = a[ix], b[ix]
            res[ix] = (op == "~=") if (x is None or y is None) else fns[op](x, y)
        return self._logical(res)

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
        return self.concat_values([self._matrix_row_values(row) for row in expr.rows])

    def concat_values(self, rows) -> Value:
        """[a b; c d] over already-evaluated values (rows of Values); used by builtins too (M10 T-E3)."""
        from openmatlab.runtime.cell_value import CellValue
        from openmatlab.runtime.char_value import CharValue

        flat = [v for r in rows for v in r]
        if any(_is_class_obj(v) for v in flat):  # horzcat/vertcat overloads (O-E4)
            return self._concat_objects(rows)
        if any(getattr(v, "is_table", False) for v in flat):  # table concatenation (M10 T-E1)
            from openmatlab.runtime import table_subs as _ts

            return _ts.concat(self, rows)
        if any(getattr(v, "is_categorical", False) for v in flat):  # (M10 T-E2)
            from openmatlab.runtime import categorical_value as _cat

            return _cat.concat(rows)
        from openmatlab.libs import datetime_arrays as _dta

        if any(_dta.is_time(v) for v in flat):  # datetime/duration/calendarDuration arrays (M10 T-E5)
            return _dta.concat(rows)
        if any(getattr(v, "is_missing_value", False) for v in flat):  # [1 missing], ["a" missing] (#504)
            from openmatlab.runtime import missing_value as _mv

            if not any(isinstance(v, CellValue) for v in flat):
                stringy = any(getattr(v, "is_string", False) for v in flat)
                rows = [_mv.resolve(r, stringy=stringy) for r in rows]
                flat = [v for r in rows for v in r]
        if any(getattr(v, "is_struct", False) for v in flat):  # (#506)
            from openmatlab.runtime import struct_eval as _se

            return _se.concat_structs(rows)
        if any(isinstance(v, CellValue) for v in flat):
            return self._concat_cells(rows)
        if any(getattr(v, "is_string", False) for v in flat):
            return self._concat_strings(rows)
        if any(isinstance(v, CharValue) for v in flat):
            return self._concat_chars(rows)
        out = self._concat_arrays(rows)
        nonempty = [v for v in flat if getattr(v, "numel", lambda: 1)() != 0]
        if nonempty and all(getattr(v, "is_graphics_handle", False) for v in nonempty):  # [h1 h2] (#768)
            out = nonempty[0].rewrap(out)
        return out

    def _concat_objects(self, rows):
        def cat(name, parts):
            parts = [p for p in parts if not (getattr(p, "numel", None) and not _is_class_obj(p) and p.numel() == 0)]
            if len(parts) == 1:
                return parts[0]
            out = self._overload(name, parts)
            if out is NotImplemented:
                from openmatlab.runtime import enums as _en

                out = _en.concat(name, parts)
            if out is NotImplemented:
                from openmatlab.runtime import object_array as _oa

                out = _oa.concat(name, parts)
            if out is NotImplemented:
                cls = next(p for p in parts if _is_class_obj(p)).matlab_class()
                raise EvalError(f"Concatenation of '{cls}' objects requires a {name} method "
                                "(object arrays are not supported yet).", "MATLAB:class:concatenation")
            return out

        hs = [cat("horzcat", r) for r in rows if r]
        return cat("vertcat", hs) if hs else self.numerics.from_nested([])

    def _matrix_row_values(self, row) -> list:
        from openmatlab.runtime.cell_value import CellValue

        out: list = []
        for el in row:
            if isinstance(el, (ast.FieldExpr, ast.CellIndexExpr)):  # [s.f], [c{:}] expand the cs-list (#506, #766)
                out.extend(self._cs_values(el))
                continue
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
        from openmatlab.numerics import sparse as _sp

        native = _sp.concat_native(rows)
        if native is not None:
            return native  # [S F; ...] in compressed storage (#517)

        int_dt = next(
            (p.dtype for r in rows for v in r
             for p in [np.asarray(v.backend_buffer())] if np.issubdtype(p.dtype, np.integer)),
            None,
        )
        bufs = []
        for r in rows:
            parts = []
            for v in r:
                b = np.asarray(self._require_array(v, "matrix").backend_buffer())
                b = b.reshape(1, 1) if b.ndim == 0 else (b.reshape(1, -1) if b.ndim == 1 else b)
                if int_dt is not None and b.dtype != int_dt:  # convert per part: no detour through double (#765)
                    from openmatlab.numerics.intclass import saturate

                    if np.issubdtype(b.dtype, np.integer):
                        info = np.iinfo(int_dt)
                        b = np.array([min(max(int(x), int(info.min)), int(info.max)) for x in b.reshape(-1)],
                                     dtype=int_dt).reshape(b.shape)
                    elif not np.iscomplexobj(b):
                        b = saturate(np.asarray(b, dtype=np.float64), int_dt)
                if b.shape != (0, 0):  # [] is ignored in concatenation
                    parts.append(b)
            if not parts:
                continue
            bufs.append(self._cat_nd(parts, axis=1))
        if not bufs:
            return self.numerics.from_nested([])
        out = self._cat_nd(bufs, axis=0)
        if int_dt is not None:
            # MATLAB: concatenating with integers yields the leftmost integer class
            from openmatlab.numerics.intclass import saturate

            if out.dtype != int_dt:
                out = saturate(np.asarray(out, dtype=np.float64), int_dt)
        elif out.dtype != np.bool_ and not np.iscomplexobj(out):
            out = out.astype(np.float64)
        if int_dt is None and any(
            np.asarray(v.backend_buffer()).dtype in (np.float32, np.complex64)
            for r in rows for v in r if hasattr(v, "backend_buffer")
        ):  # [single double] is single (#461)
            out = out.astype(np.complex64 if np.iscomplexobj(out) else np.float32)
        from openmatlab.numerics import sparse as _sp

        if any(_sp.is_sparse(v) for r in rows for v in r):
            return _sp.to_sparse(np.array(out))  # [S S] is sparse (#451)
        return NDArrayValue(np.array(out))

    def _cat_nd(self, parts: list, *, axis: int):
        """Concatenate 2-D or N-D blocks along axis; other dims must agree (#443)."""
        import numpy as np

        if len(parts) == 1:
            return parts[0]
        nd = max(p.ndim for p in parts)
        parts = [p.reshape(p.shape + (1,) * (nd - p.ndim)) for p in parts]
        keep = [d for d in range(nd) if d != axis]
        if len({tuple(p.shape[d] for d in keep) for p in parts}) != 1 and any(p.size for p in parts):
            parts = [p for p in parts if p.size]  # empties of any size are dropped next to data (#766)
        elif len({tuple(p.shape[d] for d in keep) for p in parts}) != 1:  # only empties: the first one's size wins
            parts = [p for p in parts if tuple(p.shape[d] for d in keep) == tuple(parts[0].shape[d] for d in keep)]
        if len({tuple(p.shape[d] for d in keep) for p in parts}) != 1:
            raise EvalError(self._CONCAT_ERR)
        return np.concatenate(parts, axis=axis)

    def _concat_strings(self, rows: list):
        """[\"a\" \"b\"; ...]: chars become one element per row, numbers convert (#459)."""
        import numpy as np
        from openmatlab.runtime import string_array as sa
        from openmatlab.runtime.value import Array

        blocks = []
        for r in rows:
            parts = []
            for v in r:
                if isinstance(v, Array) and v.numel() == 0:
                    continue  # [] is skipped
                g = sa.to_grid(v)
                if g is None:
                    raise EvalError(f"Conversion to string from {v.matlab_class()} is not possible.")
                if g.size or g.shape[0]:
                    parts.append(g)
            if not parts:
                continue
            if len({p.shape[0] for p in parts}) != 1:
                raise EvalError(self._CONCAT_ERR)
            blocks.append(np.concatenate(parts, axis=1))
        if not blocks:
            return sa.StringArray(np.empty((0, 0), dtype=object))
        if len({b.shape[1] for b in blocks}) != 1:
            raise EvalError(self._CONCAT_ERR)
        return sa.make(np.concatenate(blocks, axis=0))

    def _string_positions(self, grid):
        import numpy as np
        from openmatlab.numerics.ndarray_value import NDArrayValue

        return NDArrayValue(np.arange(1, grid.size + 1, dtype=np.float64).reshape(grid.shape, order="F"))

    def _string_index(self, target, arg_exprs: list) -> Value:
        """s(i), s(i,j), s(end), s(:), s(mask) on string arrays (#459): index a
        position map with the numeric path, then gather."""
        import numpy as np
        from openmatlab.runtime import string_array as sa

        g = sa.to_grid(target)
        pos = self._string_positions(g)
        idxs = self._eval_subscripts(pos, arg_exprs, label="index")
        try:
            out = np.asarray(self.numerics.index(pos, idxs).backend_buffer())
        except Exception as exc:
            raise EvalError(str(exc)) from exc
        if len(arg_exprs) == 1 and self._is_bare_colon(arg_exprs[0]):
            out = out.reshape(-1, 1)
        out = out.reshape(1, 1) if out.ndim == 0 else out
        flat = g.reshape(-1, order="F")
        res = np.empty(out.shape, dtype=object)
        for ix in np.ndindex(*out.shape):
            res[ix] = flat[int(out[ix]) - 1]
        return sa.make(res)

    def _string_assign(self, name: str, arr, idx_exprs: list, rhs_val: Value) -> Value:
        """s(i) = \"x\" / 'x' / 3, growth fills <missing>, s(i) = [] deletes (#459)."""
        import numpy as np
        from openmatlab.numerics.ndarray_value import NDArrayValue
        from openmatlab.runtime import string_array as sa
        from openmatlab.runtime.value import Array

        g = sa.to_grid(arr)
        n = g.size
        pos = self._string_positions(g)
        idxs = self._eval_subscripts(pos, idx_exprs, label="array assign")
        delete = isinstance(rhs_val, Array) and rhs_val.numel() == 0 and not sa.is_string(rhs_val)
        if delete:
            rg = np.empty((0, 0), dtype=object)
            rhs = rhs_val
        else:
            rg = sa.to_grid(rhs_val)
            if rg is None:
                raise EvalError(f"Conversion to string from {rhs_val.matlab_class()} is not possible.")
            rhs = NDArrayValue(np.arange(n + 1, n + rg.size + 1, dtype=np.float64).reshape(rg.shape, order="F"))
        try:
            new_pos = np.asarray(self.numerics.set_index(pos, idxs, rhs).backend_buffer())
        except Exception as exc:
            raise EvalError(f"array assign: {exc}") from exc
        if delete and len(idx_exprs) == 1 and self._is_bare_colon(idx_exprs[0]):
            new_pos = np.zeros((0, 0))
        lookup = [None] + list(g.reshape(-1, order="F")) + list(rg.reshape(-1, order="F"))
        new_pos = new_pos.reshape(1, 1) if new_pos.ndim == 0 else new_pos
        res = np.empty(new_pos.shape, dtype=object)
        for ix in np.ndindex(*new_pos.shape):
            res[ix] = lookup[int(new_pos[ix])]
        self.workspace.set(name, sa.make(res))
        return rhs_val

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
                if 0 in v.shape:
                    continue  # empty cells of any size are dropped next to data (MATLAB, #766)
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

        flat_vals = [v for r in rows for v in r]
        if any(getattr(v, "is_string", False) for v in flat_vals):
            if len(flat_vals) == 1:
                return flat_vals[0]
            raise EvalError("string arrays are not supported yet (#457 residual)")
        texts = []
        for r in rows:
            # each bracket row is a list of row-blocks; char matrices stack
            block: list = [""]
            for v in r:
                if isinstance(v, CharValue):
                    if not v.rows:
                        continue
                    if block == [""]:
                        block = [""] * len(v.rows)
                    if len(v.rows) != len(block):
                        raise EvalError(self._CONCAT_ERR)
                    block = [a + b for a, b in zip(block, v.rows)]
                    continue
                b = np.asarray(self._require_array(v, "matrix").backend_buffer())
                if b.ndim == 2 and min(b.shape) > 1:
                    raise EvalError(self._CONCAT_ERR)
                if b.size == 0:
                    continue
                if len(block) != 1:
                    raise EvalError(self._CONCAT_ERR)
                block = [block[0] + "".join(chr(int(x)) for x in b.reshape(-1))]
            texts.extend(t for t in block if t or len(block) > 1)
        if len({len(t) for t in texts}) > 1:
            raise EvalError(self._CONCAT_ERR)
        return CharValue(rows=texts)

    def _eval_colon(self, expr: ast.ColonExpr) -> Array:
        if expr.start is None or expr.stop is None:
            raise EvalError("Colon requires start and stop")
        parts = [expr.start, expr.stop] + ([expr.step] if expr.step is not None else [])
        vals = [self._require_array(self.eval_expr(p), "colon") for p in parts]
        start, stop = self._as_float(vals[0]), self._as_float(vals[1])
        step = self._as_float(vals[2]) if len(vals) == 3 else 1.0
        out = self.numerics.colon(start, stop, step)
        import numpy as np

        int_dt = next((np.asarray(v.backend_buffer()).dtype for v in vals
                       if np.issubdtype(np.asarray(v.backend_buffer()).dtype, np.integer)), None)
        if int_dt is not None:
            # int8(1):int8(3) is an int8 range (MATLAB, #72)
            from openmatlab.numerics.intclass import saturate
            from openmatlab.numerics.ndarray_value import NDArrayValue

            out = NDArrayValue(saturate(np.asarray(out.backend_buffer()), int_dt))
        return out

    def _as_float(self, val: Array) -> float:
        if not val.is_scalar():
            raise EvalError("Expected scalar")
        return float(val.backend_buffer().reshape(-1)[0])

    def _eval_relational(self, op: str, left: Array, right: Array) -> Array:
        import numpy as np
        from openmatlab.numerics.ndarray_value import NDArrayValue
        from openmatlab.numerics import sparse as _sp

        if _sp.is_sparse(left) or _sp.is_sparse(right):
            nat = _sp.relational_native(op, left, right)  # compressed (#523)
            if nat is not None:
                return nat

        a = np.asarray(left.backend_buffer())
        b = np.asarray(right.backend_buffer())
        a = a.astype(complex if np.iscomplexobj(a) else float)
        b = b.astype(complex if np.iscomplexobj(b) else float)
        if op not in ("==", "~="):
            # MATLAB: <, <=, >, >= compare real parts of complex operands (#71)
            a, b = np.real(a), np.real(b)
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
        from openmatlab.numerics import sparse as _sp

        if _sp.is_sparse(left) or _sp.is_sparse(right):
            return _sp.to_sparse(r)  # relational ops on sparse are sparse (#451)
        return NDArrayValue(r)

    def _truthy(self, val: Value) -> bool:
        arr = self._require_array(val, "condition")
        if arr.numel() == 0:
            return False
        import numpy as np

        buf = np.asarray(arr.backend_buffer()).reshape(-1)
        return bool(np.all(buf != 0))


    def _values_equal(self, a: Value, b: Value) -> bool:
        """Scalar/char equality for switch/case matching."""
        from openmatlab.runtime import enums as _en
        from openmatlab.runtime.char_value import CharValue

        en = _en.values_equal(a, b)
        if en is not None:
            return en

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
        from openmatlab.runtime.cell_value import CellValue
        from openmatlab.runtime.char_value import CharValue

        needle = self.eval_expr(stmt.expr)
        if not isinstance(needle, CharValue) and not (
            isinstance(needle, Array) and needle.numel() == 1
        ) and not getattr(needle, "is_enum", False):  # scalar enumeration member (M8 O-E5)
            raise EvalError("SWITCH expression must be a scalar or a character vector.")
        last: Value = self.numerics.from_scalar(0.0)
        for case in stmt.cases:
            for vexpr in case.values:
                cv = self.eval_expr(vexpr)
                if isinstance(cv, CellValue):  # case c: a cell-valued case matches any element (#766)
                    hit = any(self._values_equal(needle, x) for x in cv.to_obj().reshape(-1, order="F"))
                else:
                    hit = self._values_equal(needle, cv)
                if hit:
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
        import numpy as np
        from openmatlab.numerics.ndarray_value import NDArrayValue
        from openmatlab.runtime.cell_value import CellValue

        value = self.eval_expr(stmt.iterable)
        if getattr(value, "is_string", False):  # columns of a string array (#459)
            from openmatlab.runtime import string_array as sa

            g = sa.to_grid(value)
            items = [sa.make(g[:, [k]]) for k in range(g.shape[1])]
        elif getattr(value, "is_struct", False):  # columns of a struct array (#506)
            from openmatlab.runtime import struct_eval as _se

            pos = _se.positions(value).backend_buffer()
            items = [_se.from_positions(value, pos[:, [k]]) for k in range(pos.shape[1])]
        elif isinstance(value, CellValue):  # each iteration is one column of the cell (#766)
            r, c = value.shape
            items = [CellValue(rows=tuple((value.rows[i][k],) for i in range(r))) for k in range(c)] if r else []
        elif getattr(value, "issparse", False):  # columns stay sparse (#488)
            from openmatlab.numerics import sparse as _sp

            items = _sp.columns(value)  # straight from the store (#523)
        else:
            raw = np.asarray(self._require_array(value, "for").backend_buffer())
            keep = np.issubdtype(raw.dtype, np.integer) or np.iscomplexobj(raw) or raw.dtype == np.float32
            if not keep:
                raw = np.asarray(raw, dtype=float)
            if raw.ndim == 0:
                raw = raw.reshape(1, 1)
            # MATLAB iterates over columns of A(:,:) (#471).
            cols = raw.reshape(raw.shape[0], int(np.prod(raw.shape[1:])), order="F")
            if cols.shape[0] == 1:
                items = (
                    NDArrayValue(np.array([[x]], dtype=raw.dtype)) if keep
                    else self.numerics.from_scalar(float(x))
                    for x in cols[0]
                )
            else:
                items = (NDArrayValue(np.array(cols[:, [k]], dtype=raw.dtype)) for k in range(cols.shape[1]))
        if getattr(value, "is_graphics_handle", False):  # loop variable stays a handle (#768)
            items = [value.rewrap(it) for it in items]
        last: Value = self.numerics.from_scalar(0.0)
        self._loop_depth += 1
        try:
            for item in items:
                self.workspace.set(stmt.var, item)
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

    def _eval_try(self, stmt: ast.TryStmt) -> Value:
        """try/catch (Epic #530): any MATLAB error in the body runs the handler."""
        from openmatlab.runtime import errors as _er

        tok = _debugger.TRY_DEPTH.set(_debugger.TRY_DEPTH.get() + 1)  # 'caught error' stops (M11 D-E3)
        try:
            for s in stmt.body:
                self.eval_stmt(s)
        except (_BreakSignal, _ContinueSignal, _ReturnSignal):
            raise
        except Exception as exc:  # every user-visible failure is catchable (MATLAB)
            _debugger.TRY_DEPTH.reset(tok)
            tok = None
            if not isinstance(exc, EvalError):
                stack = getattr(exc, "mstack", None)
                exc = EvalError(str(exc))
                exc.mstack = stack
            me = _er.from_eval_error(exc)
            _er.record(str(exc), me.elems[0]["identifier"].text)
            if stmt.ident:
                self.workspace.set(stmt.ident, me)
            for s in stmt.handler:
                self.eval_stmt(s)
        finally:
            if tok is not None:
                _debugger.TRY_DEPTH.reset(tok)
        return self.numerics.from_scalar(0.0)

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



def np_bool(b: bool):
    import numpy as np

    return np.array([[bool(b)]])


def _char_codes(v):
    """char matrix → double code matrix (r x c); '' → 0x0."""
    import numpy as np
    from openmatlab.numerics.ndarray_value import NDArrayValue

    r, c = v.shape
    if r == 0:
        return NDArrayValue(np.zeros((0, 0), dtype=np.float64))
    return NDArrayValue(
        np.array([[float(ord(ch)) for ch in row] for row in v.rows], dtype=np.float64).reshape(r, c)
    )


def _codes_char(arr):
    """double code matrix → CharValue (2-D only)."""
    import numpy as np
    from openmatlab.runtime.char_value import CharValue

    b = np.asarray(arr.backend_buffer())
    if b.ndim > 2:
        raise EvalError("N-D char arrays are not supported")
    if b.size == 0:
        return CharValue("")
    b = b.reshape(b.shape if b.ndim == 2 else (1, -1))
    return CharValue(rows=["".join(chr(int(x)) for x in row) for row in b.real])


def _string_text(v):
    """Text of a string/char row/number for string ops; None if unsupported."""
    import numpy as np
    from openmatlab.runtime.char_value import CharValue
    from openmatlab.runtime.value import Array

    if isinstance(v, CharValue):
        return v.text
    if isinstance(v, Array) and v.numel() == 1:
        x = np.asarray(v.backend_buffer()).reshape(-1)[0]
        if np.iscomplexobj(x) or isinstance(x, (bool, np.bool_)):
            return None
        x = float(x)
        return str(int(x)) if x == int(x) and abs(x) < 1e15 else f"{x:.4f}".rstrip("0")
    return None


def _prod(xs) -> int:
    out = 1
    for x in xs:
        out *= int(x)
    return out


def _inplace_scalar_assign(ws, name, arr, idxs, rhs) -> bool:
    """x(k) = scalar in place when nothing else can observe x's buffer (#797).

    MATLAB values are copy-on-write; the evaluator normally copies the whole array on
    every element store, which makes loops O(n^2). When the variable's NDArrayValue and
    its ndarray are referenced only by the current frame (CPython reference counts),
    no other variable, cell, struct, closure or view can see the change, so storing in
    place is indistinguishable from the copy.
    """
    import sys as _sys
    import numpy as _np
    from openmatlab.numerics.ndarray_value import NDArrayValue as _ND

    if type(arr) is not _ND or type(rhs) is not _ND or len(idxs) != 1 or type(idxs[0]) is not _ND:
        return False
    buf, rb, ib = arr._data, rhs._data, idxs[0]._data
    if buf.dtype != _np.float64 or rb.dtype != _np.float64 or rb.size != 1 or ib.size != 1 \
            or ib.dtype != _np.float64 or buf.base is not None or not buf.flags.writeable:
        return False
    frames, refs = getattr(ws, "_frames", None), getattr(ws, "_refs", None)
    if not isinstance(frames, list) or not isinstance(refs, list) or not frames or not refs:
        return False  # nested-function shared workspaces etc. take the copying path
    frame = frames[-1]
    if not isinstance(frame, dict) or refs[-1].get(name) is not None or frame.get(name) is not arr:
        return False
    # referrers: frame dict, caller's ``arr`` and ``arr_a``, our parameter, getrefcount's argument
    if _sys.getrefcount(arr) > _INPLACE_ARR_REFS or _sys.getrefcount(buf) > _INPLACE_BUF_REFS:
        return False
    k = float(ib.reshape(-1)[0])
    if not (k == k and k == int(k) and 1 <= k <= buf.size):
        return False
    buf[_np.unravel_index(int(k) - 1, buf.shape, order="F")] = rb.reshape(-1)[0]
    return True


_INPLACE_ARR_REFS = 5
_INPLACE_BUF_REFS = 3


import operator as _op
import numpy as _np_fast

_F64 = _np_fast.dtype(_np_fast.float64)
_FAST_SCALAR_OPS = {"+": _op.add, "-": _op.sub, "*": _op.mul, ".*": _op.mul, "/": _op.truediv,
                    "./": _op.truediv, "<": _op.lt, "<=": _op.le, ">": _op.gt, ">=": _op.ge,
                    "==": _op.eq, "~=": _op.ne}


def _fast_scalar_binop(op, a, b):
    """1x1 double (op) 1x1 double in plain IEEE floats (#797); None means take the general path."""
    if a.dtype is not _F64 and a.dtype != _F64 or b.dtype != _F64 or a.shape != (1, 1) or b.shape != (1, 1):
        return None
    x, y = a[0, 0].item(), b[0, 0].item()
    if op in ("/", "./") and y == 0.0:
        return None  # numpy's inf/nan rules
    from openmatlab.numerics.ndarray_value import NDArrayValue

    r = _FAST_SCALAR_OPS[op](x, y)
    if type(r) is bool:
        return NDArrayValue(_np_fast.array([[r]], dtype=_np_fast.bool_))
    return NDArrayValue(_np_fast.array([[r]], dtype=_np_fast.float64))
