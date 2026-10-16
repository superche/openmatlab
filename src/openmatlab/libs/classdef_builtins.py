"""Builtins that understand classdef instances (M8).

These wrap existing builtins at registration time so the old behaviour stays
the same for non-objects.
"""

from __future__ import annotations

from typing import Callable, Dict

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue
from openmatlab.runtime import classdef as cd


def _b(x):
    return NDArrayValue(np.array([[bool(x)]]))


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def instances_equal(a, b, eq) -> bool:
    if cd.is_instance(a) or cd.is_instance(b):
        if not (cd.is_instance(a) and cd.is_instance(b)) or a.info is not b.info:
            return False
        if a.info.is_handle:
            return a is b or a.props is b.props or all(eq(a.props[k], b.props[k]) for k in a.props)
        return a.props.keys() == b.props.keys() and all(eq(a.props[k], b.props[k]) for k in a.props)
    return eq(a, b)


def _wrap_isequal(orig):
    def _eq(x, y):
        if cd.is_instance(x) or cd.is_instance(y):
            return instances_equal(x, y, _eq)
        return bool(np.asarray(orig([x, y], nargout=1)[0].backend_buffer()).reshape(-1)[0])

    def f(args, *, nargout=1):
        if any(cd.is_instance(a) for a in args):
            if len(args) < 2:
                raise _err("Not enough input arguments.", "MATLAB:minrhs")
            return (_b(all(_eq(args[0], b) for b in args[1:])),)
        return orig(args, nargout=nargout)

    return f


def _wrap_isa(orig):
    def f(args, *, nargout=1):
        if len(args) == 2 and cd.is_instance(args[0]):
            from openmatlab.runtime.char_value import CharValue

            want = args[1].text if isinstance(args[1], CharValue) else None
            if want is None:
                raise _err("isa: usage isa(obj, 'classname')")
            return (_b(args[0].info.isa(want)),)
        return orig(args, nargout=nargout)

    return f


def _wrap_isvalid(orig):
    def f(args, *, nargout=1):
        if len(args) == 1 and cd.is_instance(args[0]):
            if not args[0].info.is_handle:
                raise _err(f"Undefined function 'isvalid' for input arguments of type '{args[0].info.name}'.",
                           "MATLAB:UndefinedFunction")
            return (_b(args[0].alive),)
        if len(args) == 1 and hasattr(args[0], "valid_mask"):  # graphics handle arrays (#768)
            return (args[0].valid_mask(),)
        if len(args) == 1 and (getattr(args[0], "is_graphics_handle", False) or getattr(args[0], "is_listener", False)):
            # graphics handle (O-E6), event.listener (O-E7)
            return (_b(args[0].alive),)
        if orig is None:
            raise _err("isvalid: expected a handle object.", "MATLAB:UndefinedFunction")
        return orig(args, nargout=nargout)

    return f


def _wrap_delete(orig):
    def f(args, *, nargout=1):
        from openmatlab.runtime import events as _ev

        if args and all(isinstance(a, _ev.Listener) for a in args):  # delete(lh) (O-E7)
            for a in args:
                a.delete()
            return ()
        if args and all(cd.is_instance(a) for a in args):
            for a in args:
                if not a.info.is_handle:
                    raise _err(f"Undefined function 'delete' for input arguments of type '{a.info.name}'.",
                               "MATLAB:UndefinedFunction")
                if a.alive:
                    m = a.info.find_method("delete")
                    if m is not None:  # user destructor (O-E7 extends this)
                        m([a], nargout=0)
                    a.alive = False
                    _ev.drop(a)
            return ()
        return orig(args, nargout=nargout)

    return f


def _superclasses_names(info):
    out = []
    for s in info.supers:
        out.append(s.name)
        out.extend(n for n in _superclasses_names(s) if n not in out)
    for b in info.builtin_bases:
        if b not in out:
            out.append(b)
    if info.is_handle and "handle" not in out:
        out.append("handle")
    return out


def _superclasses(ev_resolver):
    def f(args, *, nargout=1):
        from openmatlab.runtime.cell_value import CellValue
        from openmatlab.runtime.char_value import CharValue

        if len(args) != 1:
            raise _err("Not enough input arguments." if not args else "Too many input arguments.",
                       "MATLAB:minrhs" if not args else "MATLAB:TooManyInputs")
        a = args[0]
        info = a.info if cd.is_instance(a) else None
        if info is None and isinstance(a, CharValue):
            info = cd.lookup(ev_resolver(), a.text)
        if info is None:
            return (CellValue(rows=()),)
        names = _superclasses_names(info)
        if not names:
            return (CellValue(rows=()),)
        return (CellValue(rows=tuple((CharValue(n),) for n in names)),)

    return f


# -- O-E5: enumerations, conversions, introspection, metaclass --------------------------------
_HANDLE_METHODS = ("addlistener", "delete", "eq", "findobj", "findprop", "ge", "gt", "isvalid", "le",
                   "listener", "lt", "ne", "notify")


def _cv(s):
    from openmatlab.runtime.char_value import CharValue

    return CharValue(s)


def _col(names):
    from openmatlab.runtime.cell_value import CellValue

    if not names:
        return CellValue.from_obj(np.empty((0, 1), dtype=object))
    return CellValue(rows=tuple((_cv(n),) for n in names))


def _class_of(ev_resolver, v, fname):
    """ClassInfo of an instance/enum array or of a class name, else None."""
    from openmatlab.runtime import enums

    if cd.is_instance(v) or isinstance(v, enums.EnumArray):
        return v.info
    t = getattr(v, "text", None)
    if t is not None and not getattr(v, "is_object", False):
        return cd.lookup(ev_resolver(), t)
    return None


def public_props(info):
    return [k for k, p in info.all_props().items() if not p.hidden and p.get_access == "public"]


def public_methods(info):
    names = [k for k in info.method_names()
             if info.find_method(k).access == "public" and not getattr(info.find_method(k), "attrs", {}).get("hidden")]
    if info.is_handle:
        names += [m for m in _HANDLE_METHODS if m not in names]
    return sorted(names, key=lambda n: (n.lower(), n))


def _print_list(title, names):
    from openmatlab.runtime import frames as _frames

    fp = _frames.caller(None).functions.resolve("fprintf") if _frames.depth() else None
    text = "\n" + title + "\n\n" + "".join(f"    {n}\n" for n in names) + "\n"
    if fp is not None:
        fp([_cv("%s"), _cv(text)], nargout=0)
    else:
        print(text, end="")


def _properties(args, *, nargout=1):
    if len(args) != 1:
        raise _err("Not enough input arguments." if not args else "Too many input arguments.", "MATLAB:narginchk")
    info = _class_of(_current_resolver, args[0], "properties")
    names = public_props(info) if info is not None else (list(args[0].fields) if getattr(args[0], "is_struct", False) else [])
    if info is None and not getattr(args[0], "is_struct", False) and getattr(args[0], "text", None) is None:
        names = []
    if nargout == 0:
        if info is None:
            t = getattr(args[0], "text", None) or args[0].matlab_class()
            _print_list(f"No properties for class {t} or no class {t}.", [])
        else:
            _print_list(f"Properties for class {info.name}:", names)
        return ()
    return (_col(names),)


def _methods(orig):
    def f(args, *, nargout=1):
        info = _class_of(_current_resolver, args[0], "methods") if args else None
        if info is None:
            if orig is not None:
                return orig(args, nargout=nargout)
            raise _err("Not enough input arguments." if not args else "No class found.", "MATLAB:methods:noClass")
        names = public_methods(info)
        if nargout == 0:
            _print_list(f"Methods for class {info.name}:", names)
            return ()
        return (_col(names),)

    return f


def _isenum(args, *, nargout=1):
    """isenum(A): true for an enumeration member or array (M8 O-E5)."""
    from openmatlab.runtime import enums

    if len(args) != 1:
        raise _err("Not enough input arguments." if not args else "Too many input arguments.", "MATLAB:narginchk")
    return (_b(enums.is_enum(args[0])),)


def _ismethod(args, *, nargout=1):
    if len(args) != 2:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    info = _class_of(_current_resolver, args[0], "ismethod") if getattr(args[0], "is_object", False) else None
    name = getattr(args[1], "text", None)
    if name is None:
        raise _err("Method name must be a character vector or string scalar.", "MATLAB:ismethod:InvalidName")
    if info is None:
        has = getattr(args[0], "has_method", None)
        return (_b(bool(has and has(name))),)
    return (_b(name in public_methods(info)),)


def _isprop(args, *, nargout=1):
    if len(args) != 2:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    name = getattr(args[1], "text", None)
    obj = args[0]
    if name is None:
        raise _err("Property name must be a character vector or string scalar.", "MATLAB:isprop:InvalidName")
    if cd.is_instance(obj) or getattr(obj, "is_enum_array", False):
        p = obj.info.find_prop(name)
        return (_b(p is not None and not p.hidden),)
    return (_b(False),)


def _wrap_fieldnames(orig):
    def f(args, *, nargout=1):
        if args and (cd.is_instance(args[0]) or getattr(args[0], "is_enum_array", False)):
            return (_col(public_props(args[0].info)),)
        return orig(args, nargout=nargout)

    return f


def _enumeration(args, *, nargout=1):
    from openmatlab.runtime import enums

    if len(args) != 1:
        raise _err("Not enough input arguments." if not args else "Too many input arguments.", "MATLAB:narginchk")
    info = _class_of(_current_resolver, args[0], "enumeration")
    if info is None:
        raise _err("Input must be an enumeration class name or member.", "MATLAB:class:EnumerationNameMissing")
    ms = list(enums.members(info).values())
    names = [m.enum_name for m in ms]
    if nargout == 0:
        _print_list(f"Enumeration members for class '{info.name}':", names)
        return ()
    if ms:
        g = np.empty((len(ms), 1), dtype=object)
        for i, m in enumerate(ms):
            g[i, 0] = m
        arr = enums.wrap(info, g)
    else:
        arr = enums.EnumArray(info, np.empty((0, 1), dtype=object))
    return (arr, _col(names))[: max(nargout, 1)]


def _wrap_convert(name, orig):
    def f(args, *, nargout=1):
        from openmatlab.runtime import enums

        if args and enums.is_enum(args[0]):
            v = args[0]
            ms = v.flat() if isinstance(v, enums.EnumArray) else [v]
            if name in ("char", "string", "cellstr"):
                if name == "char":
                    if len(ms) != 1:
                        w = max(len(m.enum_name) for m in ms)
                        from openmatlab.runtime.char_value import CharValue

                        return (CharValue(rows=[m.enum_name.ljust(w) for m in ms]),)
                    return (_cv(ms[0].enum_name),)
                if name == "cellstr":
                    return (_col([m.enum_name for m in ms]),)
                from openmatlab.runtime.string_array import StringArray

                return (StringArray(np.array([m.enum_name for m in ms], dtype=object).reshape(v.shape, order="F")),)
            vals = enums._values(v)
            if vals is None:
                raise _err(f"Cannot convert enumeration '{v.info.name}' to {name}; it is not derived from a numeric "
                           "class.", "MATLAB:class:EnumConversion")
            return orig([vals] + list(args[1:]), nargout=nargout)
        return orig(args, nargout=nargout)

    return f


class MetaClass:
    """meta.class for a classdef class (?Cls / metaclass(obj))."""

    is_object = True

    def __init__(self, info):
        self.info = info

    def matlab_class(self):
        return "meta.class"

    shape = (1, 1)
    ndim = 2

    def numel(self):
        return 1

    def is_scalar(self):
        return True

    def has_method(self, name):
        return False

    def get_prop(self, name):
        from openmatlab.runtime import enums
        from openmatlab.runtime.struct_value import StructValue

        info = self.info

        def sarr(rows):
            if not rows:
                return StructValue.build((0, 1), ("Name",), [])
            return StructValue.build((len(rows), 1), tuple(rows[0]), [dict(r) for r in rows])

        if name == "Name":
            return _cv(info.name)
        if name == "PropertyList":
            return sarr([{"Name": _cv(k), "DefiningClass": _cv(p.owner.name), "GetAccess": _cv(p.get_access),
                          "SetAccess": _cv(p.set_access), "Constant": _b(p.constant), "Dependent": _b(p.dependent),
                          "Hidden": _b(p.hidden), "Abstract": _b(p.abstract)} for k, p in info.all_props().items()])
        if name == "MethodList":
            rows = []
            for k in info.method_names():
                m = info.find_method(k)
                rows.append({"Name": _cv(k), "DefiningClass": _cv(m.owner.name), "Access": _cv(m.access),
                             "Static": _b(m.static)})
            return sarr(rows)
        if name == "SuperclassList":
            return sarr([{"Name": _cv(n)} for n in _superclasses_names(info)])
        if name == "EnumerationMemberList":
            return sarr([{"Name": _cv(n)} for n in enums.members(info)])
        if name == "Enumeration":
            return _b(bool(enums.members(info)))
        if name == "HandleCompatible":
            return _b(info.is_handle)
        if name == "Abstract":
            return _b(info.is_abstract)
        if name == "ContainingPackage":
            pkg = info.name.rpartition(".")[0]
            return _cv(pkg) if pkg else NDArrayValue(np.zeros((0, 0)))
        raise _err(f"Unrecognized method, property, or field '{name}' for class 'meta.class'.",
                   "MATLAB:noSuchMethodOrField")

    def index(self, args):
        return self

    def assign(self, args, value):
        raise _err("meta.class objects are read-only.", "MATLAB:class:SetProhibited")

    def binop(self, op, other, reflected):
        if op in ("==", "~=") and isinstance(other, MetaClass):
            same = other.info is self.info
            return _b(same if op == "==" else not same)
        return NotImplemented

    def display_text(self):
        return f"  meta.class\n\n    Name: '{self.info.name}'"


def metaclass_for(ev, name: str):
    info = cd.lookup(ev.functions, name)
    if info is None:
        raise _err(f"Unable to find class '{name}'.", "MATLAB:class:InvalidClass")
    return MetaClass(info)


def _metaclass(args, *, nargout=1):
    if len(args) != 1:
        raise _err("Not enough input arguments." if not args else "Too many input arguments.", "MATLAB:narginchk")
    info = _class_of(_current_resolver, args[0], "metaclass") if getattr(args[0], "is_object", False) else None
    if info is None:
        raise _err(f"metaclass is only available for classdef objects (got '{args[0].matlab_class()}').",
                   "MATLAB:class:metaclassUnavailable")
    return (MetaClass(info),)


def register_late(builtins: Dict[str, Callable]) -> None:
    if "isequal" in builtins:
        builtins["isequal"] = _wrap_isequal(builtins["isequal"])
    if "isa" in builtins:
        builtins["isa"] = _wrap_isa(builtins["isa"])
    builtins["isvalid"] = _wrap_isvalid(builtins.get("isvalid"))
    if "delete" in builtins:
        builtins["delete"] = _wrap_delete(builtins["delete"])
    builtins["superclasses"] = _superclasses(_current_resolver)
    builtins["properties"] = _properties
    builtins["methods"] = _methods(builtins.get("methods"))
    builtins["ismethod"] = _ismethod
    builtins["isprop"] = _isprop
    if "fieldnames" in builtins:
        builtins["fieldnames"] = _wrap_fieldnames(builtins["fieldnames"])
    builtins["enumeration"] = _enumeration
    builtins["isenum"] = _isenum
    from openmatlab.runtime import events as _events

    builtins["addlistener"] = _events.addlistener
    builtins["listener"] = _events.listener
    builtins["notify"] = _events.notify
    builtins["metaclass"] = _metaclass
    for n in ("char", "string", "cellstr", "double", "single", "logical", "int8", "int16", "int32", "int64",
              "uint8", "uint16", "uint32", "uint64"):
        if n in builtins:
            builtins[n] = _wrap_convert(n, builtins[n])


def _current_resolver():
    from openmatlab.runtime import frames as _frames

    ev = _frames.caller(None) if hasattr(_frames, "caller") else None
    return getattr(ev, "functions", None)
