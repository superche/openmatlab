"""Interactive display policy — semicolon suppress, ans, pretty-print."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Protocol, TextIO, runtime_checkable

if TYPE_CHECKING:
    from openmatlab.runtime.value import Value
    from openmatlab.runtime.workspace import Workspace


@runtime_checkable
class DisplayPolicy(Protocol):
    def should_print(self, suppress: bool) -> bool: ...

    def show(self, value: Value, *, name: Optional[str] = None) -> None: ...

    def bind_ans(self, value: Value) -> None: ...


class NullDisplay:
    def should_print(self, suppress: bool) -> bool:
        return not suppress

    def show(self, value: object, *, name: Optional[str] = None) -> None:
        return None

    def bind_ans(self, value: object) -> None:
        return None


class ConsoleDisplay:
    """Pretty-print Arrays; optionally bind ans into a workspace."""

    def __init__(
        self,
        workspace: Optional["Workspace"] = None,
        stream: Optional[TextIO] = None,
    ) -> None:
        import sys

        self.workspace = workspace
        self.stream = stream or sys.stdout

    def should_print(self, suppress: bool) -> bool:
        return not suppress

    def bind_ans(self, value: object) -> None:
        if self.workspace is not None:
            self.workspace.set("ans", value)  # type: ignore[arg-type]

    def show(self, value: object, *, name: Optional[str] = None) -> None:
        label = name if name is not None else "ans"
        pages = _nd_pages(value)
        if pages is not None:
            # MATLAB shows N-D arrays page by page: A(:,:,k) = ... (#74)
            for suffix, page in pages:
                self.stream.write(f"{label}(:,:,{suffix}) =\n\n{format_array(page)}\n\n")
            self.stream.flush()
            return
        text = _format_value(value)
        self.stream.write(f"{label} =\n\n{text}\n\n")
        self.stream.flush()


def _nd_pages(value: object):
    """For an N-D Array, [(\"k\" or \"k,l\", 2-D page), ...] in column-major
    page order; None for 2-D values."""
    try:
        from openmatlab.runtime.value import Array
        import numpy as np
    except Exception:  # pragma: no cover
        return None
    if not isinstance(value, Array):
        return None
    a = np.asarray(value.backend_buffer())
    if a.ndim <= 2 or a.size == 0:
        return None
    out = []
    for idx in np.ndindex(*a.shape[:1:-1]):
        idx = idx[::-1]  # first page dim varies fastest (column-major)
        out.append((",".join(str(i + 1) for i in idx), a[(slice(None), slice(None)) + idx]))
    return out


def _cell_int_summary(v: object):
    """MATLAB shows non-scalar integer arrays inside cells as ``[1x2 int8]`` (#464)."""
    import numpy as np

    from openmatlab.numerics.intclass import class_name
    from openmatlab.runtime.value import Array

    if not isinstance(v, Array):
        return None
    a = np.asarray(v.backend_buffer())
    cls = class_name(a.dtype) if np.issubdtype(a.dtype, np.integer) else None
    if cls is None or a.size == 1:
        return None
    shape = a.shape if a.ndim >= 2 else (1,) * (2 - a.ndim) + a.shape
    return "[" + "x".join(str(d) for d in shape) + f" {cls}]"


def _format_value(value: object) -> str:
    try:
        from openmatlab.runtime.cell_value import CellValue

        if isinstance(value, CellValue):
            r, c = value.shape
            if r == 0 and c == 0:
                return "{}  (empty cell)"
            lines = [f"{{{r}x{c} cell}}"]
            for i in range(r):
                for j in range(c):
                    inner = _cell_int_summary(value.get(i, j)) or _format_value(value.get(i, j))
                    # indent multi-line
                    inner_lines = inner.splitlines() or [inner]
                    lines.append(f"  ({i+1},{j+1}) = {inner_lines[0]}")
                    for extra in inner_lines[1:]:
                        lines.append(f"           {extra}")
            return "\n".join(lines)
    except Exception:
        pass
    from openmatlab.runtime.function_handle import FunctionHandleValue

    if isinstance(value, FunctionHandleValue):
        return value.name if value.name.startswith("@") else "@" + value.name
    try:
        from openmatlab.runtime.char_value import CharValue

        if getattr(value, "is_string", False):
            return f'"{value.text}"'
        if isinstance(value, CharValue):
            return "\n".join(value.rows)
    except Exception:
        pass
    try:
        from openmatlab.numerics.ndarray_value import NDArrayValue
        from openmatlab.runtime.value import Array

        if isinstance(value, Array):
            return format_array(value.backend_buffer())
    except Exception:
        pass
    return str(value)


def _fmt_real(v: float, integer: bool) -> str:
    if v != v:
        return "NaN"
    if v in (float("inf"), float("-inf")):
        return "Inf" if v > 0 else "-Inf"
    if integer:
        return str(int(v))
    return f"{v:.4f}"


def format_array(buf: object, terminal_width: int = 80) -> str:
    """MATLAB/Octave ``format short`` text for a 2-D array (no NumPy repr).

    Integer-valued (and logical) data prints as integers; otherwise 4 decimals,
    when magnitudes leave [1e-4, 1e5) matrices get a common ``1.0e+NN *``
    scale header (scalars use ``%.4e``). Wider than ``terminal_width``
    pages into ``Columns i through j`` blocks. Columns are
    right-aligned to a shared width with a 3-space gutter; scalars are bare.
    Empty arrays print ``[](RxC)``.
    """
    import numpy as np

    a = np.asarray(buf)
    if a.ndim == 0:
        a = a.reshape(1, 1)
    elif a.ndim == 1:
        a = a.reshape(1, -1)
    if a.ndim > 2 and a.size:
        from openmatlab.numerics.intclass import class_name

        cls = class_name(a.dtype) if np.issubdtype(a.dtype, np.integer) else "double"
        return "[" + "x".join(str(d) for d in a.shape) + f" {cls}]"
    if a.size == 0:
        return "[](" + "x".join(str(d) for d in a.shape) + ")"
    if np.iscomplexobj(a):
        return _format_complex(a, terminal_width)
    int_class = np.issubdtype(a.dtype, np.integer)
    if int_class:
        # MATLAB integer classes: exact digits, 2-space gutter (#72)
        cells = [[str(int(v)) for v in row] for row in a]
        if a.size == 1:
            return cells[0][0]
        width = max(len(c) for row in cells for c in row) + 2
        return _page_columns(cells, width, terminal_width)
    a = a.astype(np.float64)
    finite = a[np.isfinite(a)]
    integer = bool(np.all(finite == np.floor(finite))) and (
        finite.size == 0 or float(np.max(np.abs(finite))) < 1e15
    )
    header = ""
    if integer:
        cells = [[_fmt_real(v, True) for v in row] for row in a]
    else:
        nz = np.abs(finite[finite != 0])
        sci = nz.size > 0 and (float(nz.max()) >= 1e5 or float(nz.min()) < 1e-4)
        # matrices: MATLAB scales once max|x| >= 1e3 (e.g. [1000.5 2000])
        big = 1e5 if a.size == 1 else 1e3
        sci = nz.size > 0 and (float(nz.max()) >= big or float(nz.min()) < 1e-4)
        if sci and a.size == 1:
            cells = [[f"{float(a[0, 0]):.4e}"]]
        else:
            # MATLAB format short: matrices share a common scale factor
            # 10^e with e = floor(log10(max|x|)); no header when e == 0 (#417).
            e = int(np.floor(np.log10(float(nz.max())))) if sci else 0
            scale = 10.0 ** e
            if e:
                header = f"   1.0e{e:+03d} *\n\n"
            cells = [[_fmt_real(v / scale if np.isfinite(v) else v, False) for v in row] for row in a]
    if a.size == 1:
        return cells[0][0]
    width = max(len(c) for row in cells for c in row) + 3
    return header + _page_columns(cells, width, terminal_width)


def _page_columns(cells, width: int, terminal_width: int) -> str:
    """Rows of right-aligned cells; split into MATLAB 'Columns i through j'
    blocks when the matrix is wider than the terminal (#417)."""
    ncols = len(cells[0])
    per = max(1, terminal_width // width)
    if ncols <= per:
        return "\n".join("".join(c.rjust(width) for c in row) for row in cells)
    blocks = []
    for start in range(0, ncols, per):
        stop = min(start + per, ncols)
        title = (
            f"  Column {start + 1}"
            if stop - start == 1
            else f"  Columns {start + 1} through {stop}"
        )
        body = "\n".join("".join(c.rjust(width) for c in row[start:stop]) for row in cells)
        blocks.append(f"{title}\n\n{body}")
    return "\n\n".join(blocks)


def _format_complex(a, terminal_width: int = 80) -> str:
    """MATLAB format short complex: ``3 + 4i`` (integer-valued) or
    ``1.5000 - 2.0000i``; real and imaginary parts right-aligned per column (#71)."""
    import numpy as np

    re_, im_ = a.real, a.imag
    parts = np.concatenate([re_[np.isfinite(re_)], im_[np.isfinite(im_)]])
    integer = bool(np.all(parts == np.floor(parts))) and (
        parts.size == 0 or float(np.max(np.abs(parts))) < 1e15
    )

    # Large/small magnitudes (#453): scalars use %.4e per part, matrices a
    # common ``1.0e+NN *`` factor (thresholds as for real format short).
    nz = np.abs(parts[parts != 0])
    big = 1e5 if (a.size == 1 or integer) else 1e3
    sci = nz.size > 0 and (float(nz.max()) >= big or (not integer and float(nz.min()) < 1e-4))
    header = ""
    if sci:
        if a.size == 1:
            z = complex(a.reshape(-1)[0])
            sg = "-" if (z.imag < 0 or (z.imag == 0 and np.signbit(z.imag))) else "+"
            fe = lambda v: f"{v:.4e}" if np.isfinite(v) else _fmt_real(v, True)  # noqa: E731
            return f"{fe(z.real)} {sg} {fe(abs(z.imag))}i"
        e = int(np.floor(np.log10(float(nz.max()))))
        if e:
            header = f"   1.0e{e:+03d} *\n\n"
        re_, im_ = re_ / 10.0 ** e, im_ / 10.0 ** e
        integer = False

    def mag(v: float) -> str:
        return _fmt_real(abs(v), integer) if np.isfinite(v) else _fmt_real(abs(v), True)

    reals = [[_fmt_real(float(v), integer) for v in row] for row in re_]
    imags = [[mag(float(v)) for v in row] for row in im_]
    signs = [["-" if (v < 0 or (v == 0 and np.signbit(v))) else "+" for v in row] for row in im_]
    if a.size == 1:
        return f"{reals[0][0]} {signs[0][0]} {imags[0][0]}i"
    rw = max(len(x) for row in reals for x in row)
    iw = max(len(x) for row in imags for x in row)
    cells = [
        [f"{r.rjust(rw)} {sg} {i.rjust(iw)}i" for r, sg, i in zip(rr, ss, ii)]
        for rr, ss, ii in zip(reals, signs, imags)
    ]
    width = max(len(c) for row in cells for c in row) + 3
    return header + _page_columns(cells, width, terminal_width)
