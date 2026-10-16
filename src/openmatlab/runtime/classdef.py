"""classdef runtime (M8 Object system).

First principles:
- **A class is a container of ordinary functions.** The class file is parsed once
  (``lang/classdef_parser``). Methods are ``MFileCallable`` functions, and
  property defaults are ordinary expressions.
- **An instance is a record of property values plus its class.** Value objects
  copy on write: every property set returns a new instance, so sharing a Python
  object between variables is safe. Handle objects mutate in place, and every
  copy is the same Python object.
- **Dispatch is by argument.** A function call ``f(a, b)`` runs the method ``f``
  of the first object argument whose class defines it, ahead of path functions
  and builtins (MATLAB precedence). ``obj.f(...)`` is the same call.
- **Access is checked against the running method's class.** This is a
  ContextVar stack pushed by every method call.
"""

from __future__ import annotations

from pathlib import Path
import contextvars
from typing import Any, Dict, List, Optional, Sequence

_CTX: contextvars.ContextVar = contextvars.ContextVar("om_class_ctx", default=())
_IN_ACCESSOR: contextvars.ContextVar = contextvars.ContextVar("om_class_accessor", default=frozenset())

BUILTIN_BASES = {"handle", "double", "single", "logical", "char",
                 "int8", "int16", "int32", "int64", "uint8", "uint16", "uint32", "uint64",
                 "matlab.mixin.Copyable", "dynamicprops", "matlab.mixin.SetGet"}
HANDLE_BASES = {"handle", "matlab.mixin.Copyable", "dynamicprops", "matlab.mixin.SetGet"}


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _empty():
    import numpy as np

    from openmatlab.numerics.ndarray_value import NDArrayValue

    return NDArrayValue(np.zeros((0, 0)))


def _bool(b):
    import numpy as np

    from openmatlab.numerics.ndarray_value import NDArrayValue

    return NDArrayValue(np.array([[bool(b)]]))


# =============================================================================
# class model
# =============================================================================
class MethodInfo:
    def __init__(self, name: str, fn: Any, attrs: Dict[str, object], owner: "ClassInfo"):
        self.name, self.fn, self.attrs, self.owner = name, fn, attrs, owner
        self.static = bool(attrs.get("static"))
        self.access = str(attrs.get("access", "public")).lower()

    def __call__(self, args, *, nargout=1, prebind=None):
        tok = _CTX.set(_CTX.get() + (self.owner,))
        try:
            return self.fn(list(args), nargout=nargout, prebind=prebind)
        finally:
            _CTX.reset(tok)


class PropInfo:
    def __init__(self, decl, owner: "ClassInfo"):
        self.name, self.default, self.owner = decl.name, decl.default, owner
        a = decl.attrs
        acc = str(a.get("access", "public")).lower()
        self.get_access = str(a.get("getaccess", acc)).lower()
        self.set_access = str(a.get("setaccess", acc)).lower()
        self.constant = bool(a.get("constant"))
        self.dependent = bool(a.get("dependent"))
        self.hidden = bool(a.get("hidden"))
        self.abstract = bool(a.get("abstract"))
        self.dims = getattr(decl, "dims", None)
        self.cls = getattr(decl, "cls", None)
        self.validators = tuple(getattr(decl, "validators", ()) or ())

    @property
    def has_spec(self) -> bool:
        return bool(self.dims is not None or self.cls or self.validators)

    def _fail(self, msg, ident):
        return _err(f"Error setting property '{self.name}' of class '{self.owner.name}'. {msg}", ident)

    def validate(self, value):
        """Property validation (O-E3): class conversion, size, then validator functions."""
        if not self.has_spec:
            return value
        from openmatlab.numerics.ndarray_value import NDArrayValue
        import numpy as np

        R = self.owner.resolver
        call = lambda f, *xs: R.resolve(f)(list(xs), nargout=1)[0]
        if self.cls:
            cur = call("class", value)
            cur = getattr(cur, "text", cur)
            lc = self.cls.lower()
            ok = cur == self.cls or (is_instance(value) and value.info.isa(self.cls))
            if not ok:
                conv = lc in ("double", "single", "logical", "char", "string", "int8", "int16", "int32",
                              "int64", "uint8", "uint16", "uint32", "uint64")
                try:
                    if not conv:
                        raise ValueError
                    value = call(lc, value)
                except Exception:
                    raise self._fail(f"Value must be '{self.cls}' or be convertible to '{self.cls}'.",
                                     "MATLAB:validation:UnableToConvert") from None
        if self.dims is not None:
            sz = [int(x) for x in np.asarray(call("size", value).backend_buffer()).reshape(-1)]
            want = list(self.dims)
            n = max(len(sz), len(want))
            szp, wp = sz + [1] * (n - len(sz)), want + [1] * (n - len(want))
            fits = lambda a: all(w is None or w == x for w, x in zip(wp, a))
            if not fits(szp):
                numel = int(np.prod(sz))
                vec = sum(1 for x in sz if x != 1) <= 1
                if numel == 1 and all(w is not None for w in wp):
                    value = call("repmat", value, NDArrayValue(np.array([[float(w) for w in wp]])))
                elif vec and sum(1 for w in wp if w != 1) == 1:
                    tgt = [float(numel) if w != 1 else 1.0 for w in wp]
                    if fits([int(t) for t in tgt]):
                        value = call("reshape", value, NDArrayValue(np.array([tgt])))
                    else:
                        raise self._size_err()
                else:
                    raise self._size_err()
        for v in self.validators:
            self._run_validator(v, value)
        return value

    def _size_err(self):
        d = "-by-".join(":" if w is None else str(w) for w in self.dims)
        return self._fail(f"Value must be {d}.", "MATLAB:validation:IncompatibleSize")

    def _run_validator(self, expr, value):
        from openmatlab.lang import ast_nodes as ast

        name, args = None, []
        if isinstance(expr, ast.Name):
            name = expr.id
        elif isinstance(expr, (ast.CallExpr, ast.IndexExpr)) and isinstance(getattr(expr, "func", getattr(expr, "target", None)), ast.Name):
            name = getattr(expr, "func", getattr(expr, "target", None)).id
            raw = list(getattr(expr, "args", None) or getattr(expr, "indices", ()))
            if raw and isinstance(raw[0], ast.Name) and raw[0].id == self.name:
                raw = raw[1:]
            args = [self.owner._eval(a) for a in raw]
        if name is None:
            raise self._fail("Invalid validation function.", "MATLAB:validation:InvalidValidator")
        try:
            self.owner.resolver.resolve(name)([value] + args, nargout=0)
        except Exception as e:
            msg = getattr(e, "message", None) or (e.args[0] if e.args else str(e))
            raise self._fail(str(msg), getattr(e, "identifier", "") or "MATLAB:validators:failed") from None

    def implicit_default(self):
        """Default of a property with a class/size spec and no explicit default (MATLAB: zeros of the class)."""
        import numpy as np
        from openmatlab.numerics.ndarray_value import NDArrayValue

        lc = (self.cls or "").lower()
        numeric = lc in ("double", "single", "logical", "int8", "int16", "int32", "int64",
                         "uint8", "uint16", "uint32", "uint64")
        if not numeric:
            return None
        shape = (0, 0)
        if self.dims is not None and all(d is not None for d in self.dims):
            shape = tuple(self.dims)
        v = NDArrayValue(np.zeros(shape))
        return self.owner.resolver.resolve(lc)([v], nargout=1)[0] if lc != "double" else v


class ClassInfo:
    def __init__(self, node, resolver, path, full_name: str):
        from openmatlab.runtime.functions import MFileCallable, _ScopedResolver

        self.node, self.resolver, self.path = node, resolver, path
        self.name = full_name
        self.short = full_name.rsplit(".", 1)[-1]
        self.supers: List[ClassInfo] = []
        self.builtin_bases: List[str] = []
        for s in node.supers:
            if s in BUILTIN_BASES:
                self.builtin_bases.append(s)
                continue
            sup = lookup(resolver, s)
            if sup is None:
                raise _err(f"The specified superclass '{s}' contains a parse error, cannot be found on "
                           "MATLAB's search path, or is shadowed by another file with the same name.",
                           "MATLAB:class:InvalidSuperClass")
            self.supers.append(sup)
        self.is_handle = any(b in HANDLE_BASES for b in self.builtin_bases) or any(s.is_handle for s in self.supers)
        if self.is_handle and any(not s.is_handle for s in self.supers):
            raise _err("A class cannot have both handle and value superclasses.", "MATLAB:class:handleAndValue")
        # own members
        self.own_props: Dict[str, PropInfo] = {p.name: PropInfo(p, self) for p in node.props}
        local = {}
        self.own_methods: Dict[str, MethodInfo] = {}
        self.getters: Dict[str, MethodInfo] = {}
        self.setters: Dict[str, MethodInfo] = {}
        defs = []
        methods = list(node.methods)
        folder = Path(path).parent if path else None
        if folder is not None and folder.name == "@" + self.short:  # class folder (#766)
            from openmatlab.lang.classdef_parser import MethodDecl
            from openmatlab.runtime.functions import parse_mfile

            have = {m.defn.name for m in methods}
            for f in sorted(folder.iterdir()):
                if f.suffix not in (".m", ".M") or f.stem == self.short or f.stem in have or not f.is_file():
                    continue
                try:
                    defn = parse_mfile(f)
                except (ValueError, Exception):
                    continue  # a broken method file fails when called, not at class load
                methods.append(MethodDecl(defn, dict(node.signatures.get(defn.name, {}))))
                path_of = getattr(self, "_method_files", {})
                path_of[defn.name] = f
                self._method_files = path_of
        for m in methods:
            fn = MFileCallable(defn=m.defn, numerics=getattr(resolver, '_numerics', None), plots=getattr(resolver, '_plots', None),
                               resolver=resolver, source_path=getattr(self, "_method_files", {}).get(m.defn.name, path),
                               qualname=None if m.attrs.get("_local") else f"{self.short}.{m.defn.name}")
            defs.append((m, fn))
            if m.attrs.get("_local"):
                local[m.defn.name.lower()] = fn
        scope = _ScopedResolver(resolver, local) if local else None
        for m, fn in defs:
            if scope is not None:
                fn.scope = scope
            if m.attrs.get("_local"):
                continue
            info = MethodInfo(m.defn.name, fn, m.attrs, self)
            nm = m.defn.name
            if nm.startswith("get."):
                self.getters[nm[4:]] = info
            elif nm.startswith("set."):
                self.setters[nm[4:]] = info
            else:
                self.own_methods[nm] = info
        self._defaults: Optional[Dict[str, Any]] = None
        self._constants: Dict[str, Any] = {}
        self._enum_members: Optional[Dict[str, Any]] = None

    # -- hierarchy -----------------------------------------------------------
    def mro(self) -> List["ClassInfo"]:
        key = tuple(map(id, self.supers))
        hit = self.__dict__.get("_om_mro")
        if hit is not None and hit[0] == key:  # memoised (#797); a fresh list so callers may mutate it
            return list(hit[1])
        out = self._mro_walk()
        self.__dict__["_om_mro"] = (key, tuple(out))
        return out

    def _mro_walk(self) -> List["ClassInfo"]:
        out: List[ClassInfo] = []
        stack = [self]
        while stack:
            c = stack.pop(0)
            if c not in out:
                out.append(c)
                stack.extend(c.supers)
        return out

    def isa(self, name: str) -> bool:
        if name == self.name:
            return True
        if name in self.builtin_bases or (name == "handle" and self.is_handle):
            return True
        return any(s.isa(name) for s in self.supers)

    def all_props(self) -> Dict[str, PropInfo]:
        out: Dict[str, PropInfo] = {}
        for c in self.mro():
            for k, p in c.own_props.items():
                out.setdefault(k, p)
        # MATLAB lists subclass properties first, then inherited ones
        return out

    def find_prop(self, name: str) -> Optional[PropInfo]:
        for c in self.mro():
            if name in c.own_props:
                return c.own_props[name]
        return None

    def find_method(self, name: str) -> Optional[MethodInfo]:
        for c in self.mro():
            m = c.own_methods.get(name)
            if m is not None:
                return m
        # MATLAB method names are case-sensitive; tolerate case only as fallback (map cached, #797)
        mro = self.mro()
        key = tuple((id(c.own_methods), len(c.own_methods)) for c in mro)
        cached = self.__dict__.get("_om_lowmap")
        if cached is None or cached[0] != key:
            low_map: Dict[str, MethodInfo] = {}
            for c in mro:
                for k, m in c.own_methods.items():
                    if k != c.short:
                        low_map.setdefault(k.lower(), m)
            cached = (key, low_map)
            self.__dict__["_om_lowmap"] = cached
        return cached[1].get(name.lower())

    def find_accessor(self, table: str, prop: str) -> Optional[MethodInfo]:
        for c in self.mro():
            m = getattr(c, table).get(prop)
            if m is not None:
                return m
        return None

    def constructor(self) -> Optional[MethodInfo]:
        return self.own_methods.get(self.short)

    def method_names(self) -> List[str]:
        out: List[str] = []
        for c in self.mro():
            for k in c.own_methods:
                if k == c.short and c is not self:
                    continue
                if k not in out:
                    out.append(k)
        return out

    # -- values ----------------------------------------------------------------
    def _eval(self, expr):
        from openmatlab.runtime.evaluator import Evaluator
        from openmatlab.runtime.workspace import Workspace

        ev = Evaluator(workspace=Workspace(), functions=self.resolver, numerics=getattr(self.resolver, '_numerics', None),
                       plots=getattr(self.resolver, '_plots', None))
        tok = _CTX.set(_CTX.get() + (self,))
        try:
            return ev.eval_expr(expr)
        finally:
            _CTX.reset(tok)

    def defaults(self) -> Dict[str, Any]:
        if self._defaults is None:
            d: Dict[str, Any] = {}
            for c in reversed(self.mro()):
                for k, p in c.own_props.items():
                    if p.constant or p.dependent or p.abstract:
                        continue
                    if p.default is not None:
                        d[k] = p.validate(self._eval(p.default))
                    else:
                        d[k] = p.implicit_default() if p.has_spec else None
                        if d[k] is None:
                            d[k] = _empty()
            order = [k for k in self.all_props() if k in d]
            self._defaults = {k: d[k] for k in order}
        return self._defaults

    def constant(self, name: str):
        p = self.find_prop(name)
        if p is None or not p.constant:
            return None
        owner = p.owner
        if name not in owner._constants:
            owner._constants[name] = owner._eval(p.default) if p.default is not None else _empty()
        return owner._constants[name]

    def abstract_members(self) -> List[str]:
        """Abstract methods/properties not implemented along the MRO (O-E3)."""
        pending: Dict[str, None] = {}
        for c in reversed(self.mro()):
            for k in c.own_methods:
                pending.pop(k, None)
            for k, p in c.own_props.items():
                if not p.abstract:
                    pending.pop(k, None)
            for k in getattr(c.node, "abstract_methods", ()):
                pending[k] = None
            for k, p in c.own_props.items():
                if p.abstract:
                    pending[k] = None
        return list(pending)

    @property
    def is_abstract(self) -> bool:
        return bool(self.node.attrs.get("abstract")) or bool(self.abstract_members())

    def new_instance(self) -> "ClassInstance":
        return ClassInstance(self, dict(self.defaults()))


class ClassConstructor:
    """What the resolver returns for a class name: calling it constructs an instance."""

    def __init__(self, info: ClassInfo):
        self.info = info

    def __call__(self, args, *, nargout=1):
        return (construct(self.info, list(args)),)


def construct(info: ClassInfo, args: list, obj: Optional["ClassInstance"] = None):
    from openmatlab.lang import ast_nodes as ast

    if obj is None:
        if info.is_abstract:
            raise _err(f"Abstract classes cannot be instantiated. Class '{info.name}' defines abstract methods "
                       "and/or properties.", "MATLAB:class:abstract")
        obj = info.new_instance()
    ctor = info.constructor()
    if ctor is None:
        if args:
            raise _err("Too many input arguments.", "MATLAB:TooManyInputs")
        for s in info.supers:  # implicit no-argument superclass constructors
            obj = construct(s, [], obj)
        return obj
    defn = ctor.fn.defn
    out = defn.outputs[0] if defn.outputs else None
    explicit = set()
    _find_super_calls(defn.body, out, explicit)
    for s in info.supers:
        if s.name not in explicit:
            obj = construct(s, [], obj)
    if out is None:
        ctor(args, nargout=0)
        return obj
    res = ctor(args, nargout=1, prebind={out: obj})
    del ast
    return res[0] if res else obj


def _find_super_calls(node, out, acc):
    from dataclasses import fields, is_dataclass

    from openmatlab.lang import ast_nodes as ast

    if isinstance(node, (list, tuple)):
        for x in node:
            _find_super_calls(x, out, acc)
        return
    if isinstance(node, ast.SuperRef):
        if node.method == out:
            acc.add(node.cls)
        return
    if is_dataclass(node):
        for f in fields(node):
            _find_super_calls(getattr(node, f.name), out, acc)


# =============================================================================
# instances
# =============================================================================
class ClassInstance:
    is_object = True
    is_class_instance = True

    def __init__(self, info: ClassInfo, props: Dict[str, Any]):
        self.info = info
        self.props = props
        self.alive = True

    # Value protocol
    def matlab_class(self) -> str:
        return self.info.name

    @property
    def shape(self):
        return (1, 1)

    @property
    def ndim(self):
        return 2

    def numel(self):
        return 1

    def is_scalar(self):
        return True

    def _check_alive(self):
        if not self.alive:
            raise _err("Invalid or deleted object.", "MATLAB:class:InvalidHandle")

    # -- raw store -----------------------------------------------------------------
    def with_raw(self, name: str, value) -> "ClassInstance":
        if self.info.is_handle:
            self.props[name] = value
            return self
        new = dict(self.props)
        new[name] = value
        return ClassInstance(self.info, new)

    # -- property protocol -----------------------------------------------------------
    def get_prop(self, name: str):
        self._check_alive()
        info = self.info
        p = info.find_prop(name)
        if p is None:
            raise _err(f"Unrecognized method, property, or field '{name}' for class '{info.name}'.",
                       "MATLAB:noSuchMethodOrField")
        _check_access(p, p.get_access, "get")
        if p.constant:
            return info.constant(name)
        key = (id(self.props), name)
        getter = info.find_accessor("getters", name)
        if getter is not None and key not in _IN_ACCESSOR.get():
            tok = _IN_ACCESSOR.set(_IN_ACCESSOR.get() | {key})
            try:
                outs = getter([self], nargout=1)
            finally:
                _IN_ACCESSOR.reset(tok)
            return outs[0]
        if p.dependent:
            if getter is None:
                raise _err(f"Get method for Dependent property '{name}' of class '{info.name}' is not defined.",
                           "MATLAB:class:NoGetMethod")
        return self.props.get(name, _empty())

    def set_prop(self, name: str, value) -> "ClassInstance":
        self._check_alive()
        info = self.info
        p = info.find_prop(name)
        if p is None:
            raise _err(f"Unrecognized property '{name}' for class '{info.name}'.", "MATLAB:noPublicFieldForClass")
        if p.constant:
            raise _err(f"Cannot set the Constant property '{name}' of class '{info.name}'.",
                       "MATLAB:class:SetProhibited")
        _check_access(p, p.set_access, "set")
        value = p.validate(value)
        key = (id(self.props), name)
        setter = info.find_accessor("setters", name)
        if setter is not None and key not in _IN_ACCESSOR.get():
            tok = _IN_ACCESSOR.set(_IN_ACCESSOR.get() | {key})
            try:
                if info.is_handle:
                    setter([self, value], nargout=0)
                    return self
                outs = setter([self, value], nargout=1)
            finally:
                _IN_ACCESSOR.reset(tok)
            out = outs[0] if outs else self
            if not isinstance(out, ClassInstance):
                raise _err(f"Set method for property '{name}' must return the object.", "MATLAB:class:SetMethodOutput")
            return out
        if p.dependent:
            raise _err(f"In class '{info.name}', no set method is defined for Dependent property '{name}'.  "
                       "A Dependent property needs a set method to assign its value.", "MATLAB:class:noSetMethod")
        return self.with_raw(name, value)

    # -- object protocol used by the evaluator ---------------------------------------
    def index(self, args):
        if not args:
            return self
        if _is_index_one(args):
            return self
        from openmatlab.runtime import object_array as _oa

        return _oa.index(self.info, _oa.grid_of(self), args)

    def assign(self, args, value):
        from openmatlab.runtime import object_array as _oa

        return _oa.assign(self.info, _oa.grid_of(self), args, value)

    def binop(self, op, other, reflected):
        if self.info.is_handle and op in ("==", "~=") and (is_instance(other) or True):
            same = other is self  # handle equality is identity (MATLAB handle.eq/ne)
            if not is_instance(other) or not other.info.is_handle:
                raise _err(f"Operator '{op}' is not supported for operands of type '{self.info.name}' and "
                           f"'{getattr(other, 'matlab_class', lambda: '?')()}'.", "MATLAB:UndefinedFunction")
            return _bool(same if op == "==" else not same)
        return NotImplemented

    def display_text(self) -> str:
        from openmatlab.host import display as _d

        if not self.alive:
            return f"  handle to deleted {self.info.name}"
        names = [k for k, p in self.info.all_props().items()
                 if not p.hidden and p.get_access == "public"]
        if not names:
            return f"  {self.info.name} with no properties."
        w = max(len(n) for n in names)
        lines = [f"  {self.info.name} with properties:", ""]
        for n in names:
            try:
                v = self.get_prop(n)
                s = _d._field_summary(v)
            except Exception:
                s = "[error]"
            lines.append(f"    {n.rjust(w)}: {s}")
        return "\n".join(lines)


def _is_index_one(args):
    import numpy as np

    try:
        return all(np.all(np.asarray(a.backend_buffer()).reshape(-1) == 1) for a in args)
    except Exception:
        return False


def _check_access(p: PropInfo, access: str, kind: str):
    if access == "public":
        return
    ctx = _CTX.get()
    cur = ctx[-1] if ctx else None
    ok = False
    if cur is not None:
        if access == "private":
            ok = cur is p.owner
        elif access in ("protected", "immutable"):
            ok = cur.isa(p.owner.name)
        else:
            ok = cur.isa(p.owner.name)
    if not ok:
        if kind == "get":
            raise _err(f"Cannot access '{p.name}' because its GetAccess is {access}.", "MATLAB:class:GetProhibited")
        raise _err(f"Cannot set the '{p.name}' property of '{p.owner.name}' because its SetAccess is {access}.",
                   "MATLAB:class:SetProhibited")


def is_instance(v) -> bool:
    return getattr(v, "is_class_instance", False)


# =============================================================================
# registry / lookup
# =============================================================================
def lookup(resolver, name: str) -> Optional[ClassInfo]:
    """ClassInfo for a class name on the path, or None."""
    try:
        fn = resolver.resolve(name)
    except Exception:
        return None
    return fn.info if isinstance(fn, ClassConstructor) else None


def dispatchable(v) -> bool:
    return is_instance(v) or hasattr(v, "call_method")


class _BuiltinObjMethod:
    """A Python-implemented object's method (inputParser ...) in call form f(obj, ...)."""

    static = False

    def __init__(self, obj, name):
        self.obj, self.name = obj, name

    def __call__(self, args, *, nargout=1, prebind=None):
        rest = list(args)
        rest.remove(self.obj) if any(a is self.obj for a in rest) else None
        return tuple(self.obj.call_method(self.name, rest, nargout))


def find_method_for_args(name: str, args: Sequence[Any]) -> Optional[MethodInfo]:
    for a in args:
        if hasattr(a, "call_method") and not is_instance(a) and a.has_method(name):
            return _BuiltinObjMethod(a, name)
        if is_instance(a):
            m = a.info.find_method(name)
            if m is not None and not m.static and m.name.lower() != m.owner.short.lower():  # not a constructor (#766)
                return m
    return None


def method_names(resolver) -> set:
    """Lower-cased method names of the classes loaded by this session's resolver."""
    return getattr(resolver, "_om_method_names", None) or set()


def register_class(info: ClassInfo) -> None:
    res = info.resolver
    names = getattr(res, "_om_method_names", None)
    if names is None:
        names = set()
        res._om_method_names = names
    for c in info.mro():
        for k in c.own_methods:
            names.add(k.lower())


# =============================================================================
# evaluator entry points
# =============================================================================
def dot_access(ev, base: ClassInstance, name: str, arg_exprs: Optional[list], nargout: int = 1) -> list:
    """obj.name or obj.name(args): property read (then indexing), or method call."""
    base._check_alive()
    p = base.info.find_prop(name)
    if p is not None:
        v = base.get_prop(name)
        if arg_exprs is None:
            return [v]
        return [ev._index_with_exprs(v, arg_exprs)]
    m = base.info.find_method(name)
    if m is not None:
        args = ev._eval_call_args(arg_exprs or [])
        if m.static:  # obj.staticMethod(args) does not pass obj (#766)
            return list(m(list(args), nargout=nargout))
        return list(m([base] + list(args), nargout=nargout))
    if base.info.is_handle and name in ("addlistener", "listener", "notify", "delete", "isvalid"):
        fn = ev.functions.resolve(name)  # obj.notify('Evt'), obj.addlistener(...) (O-E7)
        args = ev._eval_call_args(arg_exprs or [])
        return list(fn([base] + list(args), nargout=nargout))
    raise _err(f"Unrecognized method, property, or field '{name}' for class '{base.info.name}'.",
               "MATLAB:noSuchMethodOrField")


def super_call(ev, ref, arg_values: list, nargout: int = 1):
    """obj@Super(args) inside a constructor, or meth@Super(obj, ...) inside a method."""
    sup = lookup(ev.functions, ref.cls)
    if sup is None:
        raise _err(f"Unable to find superclass '{ref.cls}'.", "MATLAB:class:InvalidSuperClass")
    try:
        cur = ev.workspace.get(ref.method)
    except KeyError:
        cur = None
    if is_instance(cur) and cur.info is not sup and cur.info.isa(sup.name):  # obj@Super(args)
        new = construct(sup, list(arg_values), cur)
        ev.workspace.set(ref.method, new)
        return [new]
    m = sup.find_method(ref.method)
    if m is None:
        raise _err(f"No method '{ref.method}' with matching signature found for class '{sup.name}'.",
                   "MATLAB:class:SuperMethodNotFound")
    return list(m(list(arg_values), nargout=nargout))


def class_ref_access(ev, info: ClassInfo, name: str, arg_exprs: Optional[list], nargout: int = 1) -> list:
    """ClassName.name / ClassName.name(args): static method, Constant property or enum member."""
    m = info.find_method(name)
    if m is not None and m.static:
        return list(m(ev._eval_call_args(arg_exprs or []), nargout=nargout))
    c = info.constant(name)
    if c is not None:
        return [c if arg_exprs is None else ev._index_with_exprs(c, arg_exprs)]
    member = enum_member(info, name)
    if member is not None:
        return [member if arg_exprs is None else ev._index_with_exprs(member, arg_exprs)]
    raise _err(f"The class {info.name} has no Constant property or Static method named '{name}'.",
               "MATLAB:subscripting:classHasNoPropertyOrMethod")


def enum_member(info: ClassInfo, name: str):
    from openmatlab.runtime import enums

    return enums.member(info, name)
