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


def make_mexception(identifier: str, message: str) -> MExceptionValue:
    from openmatlab.runtime.char_value import CharValue

    stack = StructValue((0, 1), ("file", "name", "line"), ())
    d = {"identifier": CharValue(identifier), "message": CharValue(message), "stack": stack}
    return MExceptionValue((1, 1), tuple(d), (d,))


def from_eval_error(exc) -> MExceptionValue:
    ident = getattr(exc, "identifier", "") or infer_identifier(str(exc))
    return make_mexception(ident, str(exc))
