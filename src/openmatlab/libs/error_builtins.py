"""error / MException / throw / rethrow / assert / lasterr / getReport (Epic #530)."""

from __future__ import annotations

from typing import Callable, Dict

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue
from openmatlab.runtime import errors as er


def _eval_error(msg: str, ident: str = ""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, identifier=ident)


def _text(v, fn: str) -> str:
    from openmatlab.runtime.char_value import CharValue

    if isinstance(v, CharValue) or getattr(v, "is_string", False):
        return str(v.text) if hasattr(v, "text") else str(v)
    raise _eval_error(f"{fn}: expected a character vector or string scalar")


def _fmt(fmt: str, rest) -> str:
    from openmatlab.libs.text_builtins import _sprintf

    from openmatlab.runtime.char_value import CharValue

    out = _sprintf([CharValue(fmt), *rest])[0]
    return out.text if hasattr(out, "text") else str(out)


def _message_from(args, fn: str):
    """(identifier, message) per MATLAB error/MException/assert argument rules."""
    if not args:
        return "", ""
    first = _text(args[0], fn)
    if len(args) == 1:
        return "", first  # one argument: literal text, no format processing
    if er.is_identifier(first):
        return first, _fmt(_text(args[1], fn), args[2:])
    return "", _fmt(first, args[1:])


def _field(s, name):
    from openmatlab.runtime.char_value import CharValue

    if name in s.fields:
        v = s.elems[0][name]
        if isinstance(v, CharValue):
            return v.text
    return ""


def _error(args, *, nargout=1):
    if len(args) == 1 and getattr(args[0], "is_struct", False):
        s = args[0]
        msg, ident = _field(s, "message"), _field(s, "identifier")
        if not msg:
            return ()  # error(struct) with an empty message is a no-op (MATLAB)
        raise _eval_error(msg, ident)
    ident, msg = _message_from(args, "error")
    if not args or msg == "":
        return ()  # error('') does nothing (MATLAB)
    raise _eval_error(msg, ident)


def _mexception(args, *, nargout=1):
    if len(args) < 2:
        raise _eval_error("MException: requires an identifier and a message", "MATLAB:minrhs")
    ident = _text(args[0], "MException")
    if not er.is_identifier(ident):
        raise _eval_error(f"MException: '{ident}' is not a valid message identifier", "MATLAB:MException:invalidId")
    return (er.make_mexception(ident, _fmt(_text(args[1], "MException"), args[2:])),)


def _as_me(v, fn):
    if not getattr(v, "is_mexception", False):
        raise _eval_error(f"{fn}: argument must be an MException object")
    return _field(v, "identifier"), _field(v, "message")


def _throw(args, *, nargout=1):
    if len(args) != 1:
        raise _eval_error("throw: expected one MException argument")
    ident, msg = _as_me(args[0], "throw")
    raise _eval_error(msg, ident)


def _rethrow(args, *, nargout=1):
    if len(args) != 1:
        raise _eval_error("rethrow: expected one argument")
    if getattr(args[0], "is_struct", False) and not getattr(args[0], "is_mexception", False):
        return _error(args)
    ident, msg = _as_me(args[0], "rethrow")
    exc = _eval_error(msg, ident)
    exc.mstack = er.stack_frames(args[0].elems[0].get("stack"))  # rethrow keeps the original stack (MATLAB)
    raise exc


def _truthy(v) -> bool:
    b = np.asarray(v.backend_buffer())
    return b.size > 0 and bool(np.all(b != 0))


def _assert(args, *, nargout=1):
    if not args:
        raise _eval_error("Not enough input arguments.", "MATLAB:minrhs")
    if not hasattr(args[0], "backend_buffer"):
        raise _eval_error("assert: condition must be logical or numeric", "MATLAB:assertion:LogicalScalar")
    if _truthy(args[0]):
        return ()
    if len(args) == 1:
        raise _eval_error("Assertion failed.", "MATLAB:assertion:failed")
    ident, msg = _message_from(args[1:], "assert")
    if len(args) == 2:  # assert(cond, msg): message is formatted like error(msg, ...) with no args
        ident, msg = "", _text(args[1], "assert")
    raise _eval_error(msg, ident)


def _lasterr(args, *, nargout=1):
    from openmatlab.runtime.char_value import CharValue

    last = er.last()
    out = [CharValue(last["message"])]
    if nargout > 1:
        out.append(CharValue(last["identifier"]))
    if args:
        er.record(_text(args[0], "lasterr"), _text(args[1], "lasterr") if len(args) > 1 else "")
    return tuple(out)


def _getreport(args, *, nargout=1):
    """getReport(ME[, 'extended'|'basic'][, 'hyperlinks', 'on'|'off'|'default']) (#698)."""
    from openmatlab.runtime.char_value import CharValue

    if not args:
        raise _eval_error("getReport: expected an MException")
    ident, msg = _as_me(args[0], "getReport")
    opts = [_text(a, "getReport").lower() for a in args[1:]]
    kind = "extended"
    i = 0
    while i < len(opts):
        if opts[i] in ("extended", "basic"):
            kind = opts[i]
        elif opts[i] == "hyperlinks" and i + 1 < len(opts) and opts[i + 1] in ("on", "off", "default"):
            i += 1  # text output never carries hyperlinks
        else:
            raise _eval_error(f"getReport: invalid option '{opts[i]}'", "MATLAB:MException:getReport:invalidOption")
        i += 1
    frames = er.stack_frames(args[0].elems[0].get("stack"))
    return (CharValue(er.report(msg, frames, basic=kind == "basic")),)


def _isstruct_fix(orig):
    def _wrapped(args, *, nargout=1):
        if len(args) == 1 and getattr(args[0], "is_mexception", False):
            return (NDArrayValue(np.array([[False]])),)  # an MException is an object, not a struct
        return orig(args, nargout=nargout)

    return _wrapped


def register(builtins: Dict[str, Callable]) -> None:
    builtins.update(
        error=_error, mexception=_mexception, throw=_throw, rethrow=_rethrow,
        assert_=_assert, lasterr=_lasterr, getreport=_getreport,
    )
    builtins["assert"] = builtins.pop("assert_")
    if "isstruct" in builtins:
        builtins["isstruct"] = _isstruct_fix(builtins["isstruct"])
