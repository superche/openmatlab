"""inputParser (handle object) and validateattributes (#569, Core backlog).

MATLAB behaviour from the public documentation:
- Required inputs are taken first, then optional positional inputs, then
  name-value parameters.
- Parameter names match case-insensitively, and a unique prefix is accepted
  (PartialMatching).
- An optional input whose value is text matching a parameter name ends the
  positional inputs.
- ``Results`` fields are sorted alphabetically.
- ``UsingDefaults`` lists the inputs that kept their defaults.
"""

from __future__ import annotations

from typing import Callable, Dict, List

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _iperr(parser, msg, ident):
    """Include FunctionName in InputParser error messages when set (#640)."""
    fn = getattr(parser, "function_name", "") or ""
    if fn:
        if ident.startswith("MATLAB:InputParser:"):
            ident = f"MATLAB:{fn}:{ident.split(':', 2)[-1]}"
        elif ident in ("MATLAB:minrhs", "MATLAB:TooManyInputs"):
            ident = f"MATLAB:{fn}:{ident.split(':', 1)[-1]}"
        msg = f"{msg.rstrip('.')} for {fn}."
    return _err(msg, ident)


def _cv(s):
    from openmatlab.runtime.char_value import CharValue

    return CharValue(s)


def _text(v):
    from openmatlab.runtime.char_value import CharValue

    if getattr(v, "is_string", False) and hasattr(v, "data") and v.numel() == 1:
        return str(v.data.flat[0])
    if isinstance(v, CharValue) and v.shape[0] <= 1:
        return v.text
    return None


def _b(x):
    return NDArrayValue(np.array([[bool(x)]]))


def _truth(v) -> bool:
    return bool(np.all(np.asarray(v.backend_buffer()) != 0))


def _cellrow(names):
    from openmatlab.runtime.cell_value import CellValue

    return CellValue(rows=(tuple(_cv(n) for n in names),)) if names else CellValue(rows=())


class InputParserValue:
    is_object = True
    _METHODS = {"addrequired", "addoptional", "addparameter", "addparamvalue", "addswitch", "parse", "disp", "delete"}

    def __init__(self):
        self.function_name = ""
        self.case_sensitive = False
        self.keep_unmatched = False
        self.partial_matching = True
        self.struct_expand = True
        self.required: List[tuple] = []  # (name, validator)
        self.optional: List[tuple] = []  # (name, default, validator)
        self.params: List[tuple] = []    # (name, default, validator)
        self.switches: List[str] = []  # addSwitch names (#640)
        self.results: Dict[str, object] = {}
        self.unmatched: Dict[str, object] = {}
        self.using_defaults: List[str] = []

    # Value protocol
    def matlab_class(self):
        return "inputParser"

    @property
    def shape(self):
        return (1, 1)

    def numel(self):
        return 1

    def is_scalar(self):
        return True

    # object protocol
    def has_method(self, name):
        return name.lower() in self._METHODS

    def get_prop(self, name):
        from openmatlab.runtime.struct_value import StructValue

        k = name.lower()
        if k == "results":
            return StructValue.scalar((n, self.results[n]) for n in sorted(self.results))
        if k == "unmatched":
            return StructValue.scalar((n, self.unmatched[n]) for n in sorted(self.unmatched))
        if k == "usingdefaults":
            return _cellrow(self.using_defaults)
        if k == "parameters":
            return _cellrow(sorted([r[0] for r in self.required] + [o[0] for o in self.optional]
                                   + [p[0] for p in self.params] + list(self.switches), key=str.lower))
        if k == "functionname":
            return _cv(self.function_name)
        flags = {"casesensitive": "case_sensitive", "keepunmatched": "keep_unmatched",
                 "partialmatching": "partial_matching", "structexpand": "struct_expand"}
        if k in flags:
            return _b(getattr(self, flags[k]))
        raise _err(f"Unrecognized method, property, or field '{name}' for class 'inputParser'.",
                   "MATLAB:noSuchMethodOrField")

    def set_prop(self, name, value):
        k = name.lower()
        flags = {"casesensitive": "case_sensitive", "keepunmatched": "keep_unmatched",
                 "partialmatching": "partial_matching", "structexpand": "struct_expand"}
        if k == "functionname":
            t = _text(value)
            if t is None:
                raise _err("FunctionName must be a character vector.", "MATLAB:InputParser:InvalidFunctionName")
            self.function_name = t
        elif k in flags:
            setattr(self, flags[k], _truth(value))
        elif k in ("results", "unmatched", "usingdefaults", "parameters"):
            raise _err(f"You cannot set the read-only property '{name}' of inputParser.", "MATLAB:class:SetProhibited")
        else:
            raise _err(f"Unrecognized property '{name}' for class 'inputParser'.", "MATLAB:noPublicFieldForClass")
        return self

    def index(self, args):
        return self

    def binop(self, op, other, reflected):
        return NotImplemented

    def display_text(self):
        lines = ["  inputParser with properties:", ""]
        rows = [("FunctionName", f"'{self.function_name}'"), ("CaseSensitive", str(int(self.case_sensitive))),
                ("KeepUnmatched", str(int(self.keep_unmatched))), ("PartialMatching", str(int(self.partial_matching))),
                ("StructExpand", str(int(self.struct_expand)))]
        w = max(len(r[0]) for r in rows)
        lines += [f"    {k.rjust(w)}: {v}" for k, v in rows]
        return "\n".join(lines)

    # --- methods ------------------------------------------------------------------
    def call_method(self, name, args, nargout=1):
        k = name.lower()
        if k == "addrequired":
            self._add("addRequired", args, 1, 2)
            self.required.append((self._name(args[0]), args[1] if len(args) > 1 else None))
        elif k == "addoptional":
            self._add("addOptional", args, 2, 3)
            self.optional.append((self._name(args[0]), args[1], args[2] if len(args) > 2 else None))
        elif k in ("addparameter", "addparamvalue"):
            if len(args) == 4 and (_text(args[2]) or "").lower() == "partialmatchpriority":
                args = args[:2]
            self._add(name, args, 2, 3)
            self.params.append((self._name(args[0]), args[1], args[2] if len(args) > 2 else None))
        elif k == "addswitch":
            self._add("addSwitch", args, 1, 1)
            self.switches.append(self._name(args[0]))
        elif k == "parse":
            self._parse(list(args))
        elif k == "disp":
            print(self.display_text())
        elif k == "delete":
            pass
        return ()

    def _add(self, fn, args, lo, hi):
        if len(args) < lo:
            raise _err("Not enough input arguments.", "MATLAB:minrhs")
        if len(args) > hi:
            raise _err("Too many input arguments.", "MATLAB:TooManyInputs")

    def _name(self, v):
        t = _text(v)
        if t is None or not t.replace("_", "a").isalnum() or not t[:1].isalpha():
            raise _err("Argument name must be a valid MATLAB variable name.", "MATLAB:InputParser:InvalidArgName")
        existing = [r[0] for r in self.required] + [o[0] for o in self.optional] + [p[0] for p in self.params] + list(self.switches)
        if any(e.lower() == t.lower() for e in existing):
            raise _err(f"An argument named '{t}' already exists in the schema.", "MATLAB:InputParser:ParamAlreadyExists")
        return t

    def _check(self, name, value, validator):
        if validator is None:
            return
        try:
            outs = validator.call([value], nargout=1)
        except Exception as exc:
            msg = getattr(exc, "message", None) or str(exc)
            raise _iperr(self, f"The value of '{name}' is invalid. {msg}", "MATLAB:InputParser:ArgumentFailedValidation") from None
        if outs and not _truth(outs[0]):
            fname = getattr(validator, "name", "")
            raise _iperr(self, f"The value of '{name}' is invalid. It must satisfy the function: {fname.lstrip('@')}",
                         "MATLAB:InputParser:ArgumentFailedValidation")

    def _valid_quietly(self, value, validator):
        if validator is None:
            return True
        try:
            outs = validator.call([value], nargout=1)
        except Exception:
            return False
        return not outs or _truth(outs[0])

    def _match_param(self, text, *, include_switches=True):
        names = [p[0] for p in self.params] + (list(self.switches) if include_switches else [])
        if self.case_sensitive:
            exact = [n for n in names if n == text]
            pref = [n for n in names if n.startswith(text)]
        else:
            exact = [n for n in names if n.lower() == text.lower()]
            pref = [n for n in names if n.lower().startswith(text.lower())]
        if exact:
            return exact[0]
        if self.partial_matching and len(pref) == 1:
            return pref[0]
        if self.partial_matching and len(pref) > 1:
            raise _iperr(self, f"'{text}' matches multiple parameter names: {', '.join(pref)}. To avoid ambiguity, "
                         "specify the complete name of the parameter", "MATLAB:InputParser:AmbiguousParamName")
        return None

    def _parse(self, args):
        res: Dict[str, object] = {}
        given = set()
        self.unmatched = {}
        if len(args) < len(self.required):
            raise _iperr(self, "Not enough input arguments", "MATLAB:minrhs")
        k = 0
        for name, val in self.required:
            self._check(name, args[k], val)
            res[name] = args[k]
            given.add(name)
            k += 1
        param_or_sw = bool(self.params or self.switches)
        for name, default, val in self.optional:
            if k >= len(args):
                break
            t = _text(args[k])
            if t is not None and param_or_sw and self._match_param(t) is not None and \
                    not (val is not None and self._valid_quietly(args[k], val) and False):
                break
            if val is not None and not self._valid_quietly(args[k], val):
                if t is not None and param_or_sw:
                    break
                self._check(name, args[k], val)
            res[name] = args[k]
            given.add(name)
            k += 1
        rest = args[k:]
        pairs = []
        i = 0
        from openmatlab.runtime.struct_value import is_struct

        while i < len(rest):
            a = rest[i]
            if self.struct_expand and is_struct(a) and a.numel() == 1:
                pairs.extend((f, a.get(f)) for f in a.fields)
                i += 1
                continue
            t = _text(a)
            if t is None:
                raise _iperr(self, "Expected a string scalar or character vector for the parameter name",
                             "MATLAB:InputParser:ParamMustBeChar")
            # addSwitch: flag with no value (#640)
            sw = self._match_param(t)
            if sw is not None and sw in self.switches:
                pairs.append((t, _b(True)))
                i += 1
                continue
            if i + 1 >= len(rest):
                raise _iperr(self, f"No value was given for '{t}'. Name-value pair arguments require a name followed "
                             "by a value", "MATLAB:InputParser:ParamMissingValue")
            pairs.append((t, rest[i + 1]))
            i += 2
        for t, v in pairs:
            m = self._match_param(t)
            if m is None:
                if self.keep_unmatched:
                    self.unmatched[t] = v
                    continue
                raise _iperr(self, f"'{t}' is not a recognized parameter. For a list of valid name-value pair "
                             "arguments, see the documentation for this function",
                             "MATLAB:InputParser:UnmatchedParameter")
            if m in self.switches:
                res[m] = v
                given.add(m)
                continue
            val = next(p[2] for p in self.params if p[0] == m)
            self._check(m, v, val)
            res[m] = v
            given.add(m)
        defaults = []
        for name, default, _v in self.optional + self.params:
            if name not in given:
                res[name] = default
                defaults.append(name)
        for name in self.switches:
            if name not in given:
                res[name] = _b(False)
                defaults.append(name)
        self.results = res
        self.using_defaults = defaults


def _inputparser(args, *, nargout=1):
    if args:
        raise _err("Too many input arguments.", "MATLAB:TooManyInputs")
    return (InputParserValue(),)


# ---------------------------------------------------------------- validateattributes
def _classes_ok(v, classes):
    cls = v.matlab_class()
    groups = {"numeric": ("double", "single", "int8", "int16", "int32", "int64", "uint8", "uint16", "uint32", "uint64"),
              "float": ("double", "single")}
    for c in classes:
        if cls == c or cls in groups.get(c, ()):
            return True
        if getattr(v, "is_class_instance", False) and v.info.isa(c):
            return True
    return False


def _validateattributes(args, *, nargout=1):
    from openmatlab.runtime.cell_value import CellValue

    if len(args) < 3:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    A, classes, attrs = args[0], args[1], args[2]
    fname = _text(args[3]) if len(args) > 3 else ""
    vname = _text(args[4]) if len(args) > 4 else ""
    argidx = int(np.asarray(args[5].backend_buffer()).reshape(-1)[0]) if len(args) > 5 else None
    if argidx is None and len(args) > 3 and _text(args[3]) is None:
        argidx = int(np.asarray(args[3].backend_buffer()).reshape(-1)[0])
        fname = ""
    who = vname or "input"
    if argidx is not None:
        who = f"input number {argidx}, {vname}," if vname else f"input number {argidx}"

    def fail(key, desc):
        raise _err(f"Expected {who} to be {desc}.", f"MATLAB:{fname or 'validateattributes'}:expected{key}")

    cls_list = [_text(c) for c in (classes.to_obj().reshape(-1, order="F") if isinstance(classes, CellValue) else [classes])]
    cls_list = [c for c in cls_list if c]
    if cls_list and not _classes_ok(A, cls_list):
        desc = ", ".join(cls_list)
        raise _err(f"Expected {who} to be one of these types:\n\n{desc}\n\nInstead its type was {A.matlab_class()}.",
                   f"MATLAB:{fname or 'validateattributes'}:invalidType")
    items = list(attrs.to_obj().reshape(-1, order="F")) if isinstance(attrs, CellValue) else []
    try:
        a = np.asarray(A.backend_buffer())
    except Exception:
        a = None
    shape = tuple(A.shape) if hasattr(A, "shape") else (1, 1)
    i = 0

    def num(v):
        return np.asarray(v.backend_buffer(), dtype=float).reshape(-1)

    while i < len(items):
        t = (_text(items[i]) or "").lower()
        i += 1
        vals = a.astype(float) if a is not None and a.dtype != object else None
        if t in ("size", "numel", "ncols", "nrows", "ndims", ">", ">=", "<", "<="):
            arg = items[i]
            i += 1
            n = num(arg)
            if t == "size":
                want = [None if np.isnan(x) else int(x) for x in n]
                have = tuple(shape) + (1,) * (len(want) - len(shape))  # size(A, k) is 1 past ndims(A)
                if len(want) < len(shape) or any(w is not None and w != s for w, s in zip(want, have)):
                    fail("Size", "of size " + "x".join("N" if w is None else str(w) for w in want)
                         + " when it is actually size " + "x".join(str(s) for s in shape))
            elif t == "numel" and int(np.prod(shape)) != int(n[0]):
                fail("Numel", f"an array with number of elements equal to {int(n[0])}")
            elif t == "ncols" and shape[1] != int(n[0]):
                fail("NCols", f"an array with {int(n[0])} columns")
            elif t == "nrows" and shape[0] != int(n[0]):
                fail("NRows", f"an array with {int(n[0])} rows")
            elif t == "ndims" and len(shape) != int(n[0]):
                fail("NDims", f"an array with {int(n[0])} dimensions")
            elif t in (">", ">=", "<", "<=") and vals is not None:
                ops = {">": (np.greater, "greater than", "Greater"), ">=": (np.greater_equal, "greater than or equal to", "GreaterEqual"),
                       "<": (np.less, "less than", "Less"), "<=": (np.less_equal, "less than or equal to", "LessEqual")}
                fn, words, key = ops[t]
                if not np.all(fn(vals, n[0])):
                    fail(key, f"an array with all of the values {words} {n[0]:g}")
            continue
        checks = {
            "positive": ("Positive", "positive", lambda v: np.all(v > 0)),
            "nonnegative": ("Nonnegative", "nonnegative", lambda v: np.all(v >= 0)),
            "nonzero": ("Nonzero", "nonzero", lambda v: np.all(v != 0)),
            "integer": ("Integer", "integer-valued", lambda v: np.all(np.isfinite(v) & (v == np.round(v)))),
            "finite": ("Finite", "finite", lambda v: np.all(np.isfinite(v))),
            "nonnan": ("NonNaN", "non-NaN", lambda v: not np.any(np.isnan(v))),
            "real": ("Real", "real", lambda v: not np.iscomplexobj(a)),
            "even": ("Even", "even", lambda v: np.all(np.mod(v, 2) == 0)),
            "odd": ("Odd", "odd", lambda v: np.all(np.mod(v, 2) == 1)),
            "binary": ("Binary", "binary", lambda v: np.all((v == 0) | (v == 1))),
            "increasing": ("Increasing", "increasing", lambda v: np.all(np.diff(v.reshape(-1)) > 0)),
            "decreasing": ("Decreasing", "decreasing", lambda v: np.all(np.diff(v.reshape(-1)) < 0)),
            "nondecreasing": ("Nondecreasing", "nondecreasing", lambda v: np.all(np.diff(v.reshape(-1)) >= 0)),
            "nonincreasing": ("Nonincreasing", "nonincreasing", lambda v: np.all(np.diff(v.reshape(-1)) <= 0)),
        }
        shapes = {
            "scalar": ("Scalar", "a scalar", int(np.prod(shape)) == 1),
            "vector": ("Vector", "a vector", len(shape) == 2 and min(shape) == 1),
            "row": ("Row", "a row vector", len(shape) == 2 and shape[0] == 1),
            "column": ("Column", "a column vector", len(shape) == 2 and shape[1] == 1),
            "nonempty": ("Nonempty", "nonempty", int(np.prod(shape)) > 0),
            "2d": ("TwoD", "two-dimensional", len(shape) == 2),
            "3d": ("ThreeD", "an array with three or fewer dimensions", len(shape) <= 3),
            "scalartext": ("ScalarText", "a character row vector or string scalar",
                           (A.matlab_class() == "char" and len(shape) == 2 and shape[0] <= 1)
                           or (A.matlab_class() == "string" and int(np.prod(shape)) == 1)),
            "square": ("Square", "a square matrix", len(shape) == 2 and shape[0] == shape[1]),
            "nonsparse": ("Nonsparse", "nonsparse", not getattr(A, "issparse", False)),
            "diag": ("Diag", "diagonal", vals is not None and len(shape) == 2 and np.all(vals == np.diag(np.diag(vals)))),
        }
        if t in shapes:
            key, desc, ok = shapes[t]
            if not ok:
                fail(key, desc)
        elif t in checks:
            key, desc, fn = checks[t]
            if vals is None or not fn(vals.real if t != "real" else vals):
                fail(key, desc)
        else:
            raise _err(f"validateattributes: unknown attribute '{t}'.", "MATLAB:validateattributes:badAttribute")
    return ()


def register(builtins: Dict[str, Callable]) -> None:
    builtins["inputparser"] = _inputparser
    builtins["validateattributes"] = _validateattributes
