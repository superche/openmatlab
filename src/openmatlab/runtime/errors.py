"""MATLAB errors and MException values (Epic #530).

``EvalError`` carries an optional MATLAB identifier. ``MExceptionValue`` is the
object bound by ``catch e``; it reads like a struct (``e.message``,
``e.identifier``, ``e.stack``) but reports class ``MException``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from openmatlab.runtime.struct_value import StructValue

_LAST = {"message": "", "identifier": ""}

# MATLAB identifiers for errors raised by the runtime itself (public MATLAB docs).
_BUILTIN_IDS = (
    (re.compile(r"^Index exceeds|^Index in position \d+ exceeds|index exceeds"), "MATLAB:badsubscript"),
    (re.compile(r"^Undefined function or variable|^Undefined variable"), "MATLAB:UndefinedFunction"),
    (re.compile(r"^Too many input arguments|expected \d+ args, got"), "MATLAB:TooManyInputs"),
    (re.compile(r"^Not enough input arguments"), "MATLAB:minrhs"),
    (re.compile(r"[Mm]atrix dimensions must agree|Arrays have incompatible sizes|could not be broadcast"), "MATLAB:sizeDimensionsMustMatch"),
    (re.compile(r"^Unable to perform assignment because the size"), "MATLAB:subsassigndimmismatch"),
    (re.compile(r"subscripts must be positive integers|indices must be positive integers"), "MATLAB:index:expected_positive_integer"),
)

_ID_RE = re.compile(r"^[A-Za-z][\w-]*(:[\w-]+)+$")


def is_identifier(text: str) -> bool:
    return bool(_ID_RE.match(text)) and " " not in text


def infer_identifier(message: str) -> str:
    for pat, ident in _BUILTIN_IDS:
        if pat.search(message):
            return ident
    return ""


def record(message: str, identifier: str) -> None:
    """lasterr / lasterror bookkeeping: every raised error updates it (MATLAB)."""
    _LAST["message"] = message
    _LAST["identifier"] = identifier


def last():
    return dict(_LAST)


@dataclass(frozen=True)
class MExceptionValue(StructValue):
    is_mexception = True

    def matlab_class(self) -> str:
        return "MException"


def stack_struct(frames, complete: bool = True) -> StructValue:
    """(file, name, line) tuples -> MATLAB n-by-1 struct with fields file, name, line (#698)."""
    import numpy as np
    from pathlib import Path

    from openmatlab.numerics.ndarray_value import NDArrayValue
    from openmatlab.runtime.char_value import CharValue

    elems = tuple(
        {"file": CharValue(f if complete or not f else Path(f).name), "name": CharValue(n),
         "line": NDArrayValue(np.array([[float(ln)]]))}
        for f, n, ln in frames
    )
    return StructValue((len(elems), 1), ("file", "name", "line"), elems)


def stack_frames(stack) -> tuple:
    """Inverse of stack_struct: MATLAB stack struct -> (file, name, line) tuples."""
    out = []
    for e in getattr(stack, "elems", ()):
        try:
            out.append((e["file"].text, e["name"].text, int(float(e["line"].backend_buffer().ravel()[0]))))
        except (KeyError, AttributeError, IndexError, TypeError, ValueError):
            continue
    return tuple(out)


def make_mexception(identifier: str, message: str, frames=()) -> MExceptionValue:
    from openmatlab.runtime.char_value import CharValue

    d = {"identifier": CharValue(identifier), "message": CharValue(message), "stack": stack_struct(frames)}
    return MExceptionValue((1, 1), tuple(d), (d,))


def from_eval_error(exc) -> MExceptionValue:
    ident = getattr(exc, "identifier", "") or infer_identifier(str(exc))
    return make_mexception(ident, str(exc), getattr(exc, "mstack", None) or ())


def report(message: str, frames, basic: bool = False) -> str:
    """getReport / uncaught-error text, hyperlink-free (MATLAB layout)."""
    if not frames:
        return message
    _f, name, line = frames[0]
    head = f"Error using {name} (line {line})\n{message}"
    if basic:
        return head
    return head + "".join(f"\n\nError in {n} (line {ln})" for _f, n, ln in frames[1:])


def error_in_lines(frames) -> str:
    """Trailer printed after an uncaught error at the prompt: one "Error in" line per frame."""
    return "\n".join(f"Error in {n} (line {ln})" for _f, n, ln in frames)
