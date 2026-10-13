"""mustBe* validation functions (M8 O-E3, #620), used by property validation and directly."""

from __future__ import annotations

from typing import Callable, Dict

import numpy as np


def _err(msg, name):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, f"MATLAB:validators:{name}")


def _num(v):
    try:
        a = np.asarray(v.backend_buffer())
    except Exception:
        return None
    if a.dtype == object:
        return None
    return a


def _is_numeric(v):
    from openmatlab.runtime.char_value import CharValue

    if isinstance(v, CharValue) or getattr(v, "is_string", False):
        return False
    a = _num(v)
    return a is not None and a.dtype != bool and (np.issubdtype(a.dtype, np.number))


def _is_logical(v):
    a = _num(v)
    return a is not None and a.dtype == bool


def _real_num(v, name, what):
    if not (_is_numeric(v) or _is_logical(v)):
        raise _err(f"Value must be {what}.", name)
    return _num(v)


def _elem(name, test, what):
    def fn(args, *, nargout=0):
        a = _real_num(args[0], name, what)
        if a.size and not np.all(test(a)):
            raise _err(f"Value must be {what}.", name)
        return []

    return fn


def _fmt(v):
    a = np.asarray(v.backend_buffer()).reshape(-1)
    x = float(a[0]) if a.size else 0.0
    return str(int(x)) if x == int(x) else repr(x)


def _cmp(name, op, words):
    def fn(args, *, nargout=0):
        a = _real_num(args[0], name, f"{words} {_fmt(args[1])}")
        c = np.asarray(args[1].backend_buffer())
        if a.size and not np.all(op(a, c)):
            raise _err(f"Value must be {words} {_fmt(args[1])}.", name)
        return []

    return fn


def _in_range(args, *, nargout=0):
    lo, hi = _fmt(args[1]), _fmt(args[2])
    flags = [getattr(x, "text", "").lower() for x in args[3:]]
    lower_ex = "exclusive" in flags or "exclude-lower" in flags
    upper_ex = "exclusive" in flags or "exclude-upper" in flags
    what = (f"greater than {'' if lower_ex else 'or equal to '}{lo} and "
            f"less than {'' if upper_ex else 'or equal to '}{hi}")
    a = _real_num(args[0], "mustBeInRange", what)
    l, h = float(np.asarray(args[1].backend_buffer()).flat[0]), float(np.asarray(args[2].backend_buffer()).flat[0])
    ok = (a > l if lower_ex else a >= l) & (a < h if upper_ex else a <= h)
    if a.size and not np.all(ok):
        raise _err(f"Value must be {what}.", "mustBeInRange")
    return []


def _pred(name, test, msg):
    def fn(args, *, nargout=0):
        if not test(args[0]):
            raise _err(msg, name)
        return []

    return fn


def _is_text(v):
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.char_value import CharValue

    if isinstance(v, CharValue) and v.shape[0] <= 1 or getattr(v, "is_string", False):
        return True
    if isinstance(v, CellValue):
        return all(isinstance(x, CharValue) and x.shape[0] <= 1 for r in v.rows for x in r)
    return False


def _shape(v):
    sh = getattr(v, "shape", None)
    if sh is None:
        try:
            sh = np.asarray(v.backend_buffer()).shape
        except Exception:
            sh = (1, 1)
    return tuple(sh)


def register(builtins: Dict[str, Callable]) -> None:
    builtins["mustBePositive"] = _elem("mustBePositive", lambda a: a > 0, "positive")
    builtins["mustBeNonnegative"] = _elem("mustBeNonnegative", lambda a: a >= 0, "nonnegative")
    builtins["mustBeNegative"] = _elem("mustBeNegative", lambda a: a < 0, "negative")
    builtins["mustBeNonpositive"] = _elem("mustBeNonpositive", lambda a: a <= 0, "nonpositive")
    builtins["mustBeFinite"] = _elem("mustBeFinite", np.isfinite, "finite")
    builtins["mustBeNonNan"] = _elem("mustBeNonNan", lambda a: ~np.isnan(a), "non-NaN")
    builtins["mustBeReal"] = _elem("mustBeReal", np.isreal, "real")
    builtins["mustBeInteger"] = _elem("mustBeInteger", lambda a: np.isfinite(a) & (a == np.round(a)), "integer")

    def nonzero(args, *, nargout=0):
        a = _real_num(args[0], "mustBeNonzero", "nonzero")
        if a.size and not np.all(a != 0):
            raise _err("Value must not be zero.", "mustBeNonzero")
        return []

    builtins["mustBeNonzero"] = nonzero
    builtins["mustBeGreaterThan"] = _cmp("mustBeGreaterThan", np.greater, "greater than")
    builtins["mustBeGreaterThanOrEqual"] = _cmp("mustBeGreaterThanOrEqual", np.greater_equal, "greater than or equal to")
    builtins["mustBeLessThan"] = _cmp("mustBeLessThan", np.less, "less than")
    builtins["mustBeLessThanOrEqual"] = _cmp("mustBeLessThanOrEqual", np.less_equal, "less than or equal to")
    builtins["mustBeInRange"] = _in_range
    builtins["mustBeNumeric"] = _pred("mustBeNumeric", _is_numeric, "Value must be numeric.")
    builtins["mustBeNumericOrLogical"] = _pred("mustBeNumericOrLogical", lambda v: _is_numeric(v) or _is_logical(v),
                                               "Value must be numeric or logical.")
    builtins["mustBeText"] = _pred("mustBeText", _is_text,
                                   "Value must be a character vector, string array, or cell array of character vectors.")
    builtins["mustBeNonempty"] = _pred("mustBeNonempty", lambda v: 0 not in _shape(v), "Value must not be empty.")
    builtins["mustBeVector"] = _pred("mustBeVector", lambda v: len(_shape(v)) == 2 and 1 in _shape(v),
                                     "Value must be a 1-by-n or n-by-1 vector.")
    builtins["mustBeScalarOrEmpty"] = _pred("mustBeScalarOrEmpty",
                                            lambda v: int(np.prod(_shape(v))) <= 1,
                                            "Value must be scalar or empty.")
    ismember = builtins.get("ismember")

    def member(args, *, nargout=0):
        ok = ismember([args[0], args[1]], nargout=1)[0] if ismember else None
        if ok is None or not bool(np.all(np.asarray(ok.backend_buffer()))):
            raise _err("Value must be a member of the specified set.", "mustBeMember")
        return []

    builtins["mustBeMember"] = member
