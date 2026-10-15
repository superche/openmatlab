"""Events and listeners on handle classes (M8 O-E7).

``events`` blocks declare event names. ``addlistener(src, 'Evt', cb)`` and
``listener(...)`` return an ``event.listener`` handle. ``notify(src, 'Evt')``
calls every enabled listener's callback as ``cb(src, evt)``, in the order the
listeners were added. ``evt`` is an ``event.EventData`` with ``Source`` and
``EventName``. ``delete(lh)`` removes a listener. The listeners of a source live
on that source, so deleting the source drops them.
"""

from __future__ import annotations

from typing import Any, List

from openmatlab.runtime import classdef as cd


def _err(msg, ident=""):
    return cd._err(msg, ident)


def event_names(info) -> List[str]:
    out: List[str] = []
    for c in info.mro():
        for name, _attrs in getattr(c.node, "events", ()) or ():
            if name not in out:
                out.append(name)
    return out


def _text(v, what):
    t = getattr(v, "text", None)
    if t is None:
        raise _err(f"{what} must be a character vector or string scalar.", "MATLAB:class:InvalidEventName")
    return t


def _bool(x):
    import numpy as np

    from openmatlab.numerics.ndarray_value import NDArrayValue

    return NDArrayValue(np.array([[bool(x)]]))


class _Obj:
    """Small handle-like built-in object with read-only / settable properties."""

    is_object = True
    _settable: tuple = ()

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

    def _prop_names(self):
        return list(self._props())

    def get_prop(self, name: str):
        props = self._props()
        if name not in props:
            raise _err(f"Unrecognized method, property, or field '{name}' for class '{self.matlab_class()}'.",
                       "MATLAB:noSuchMethodOrField")
        return props[name]

    def display_text(self) -> str:
        lines = [f"  {self.matlab_class()} with properties:", ""]
        props = self._props()
        w = max(len(k) for k in props)
        for k, v in props.items():
            lines.append(f"    {k.rjust(w)}: {_short(v)}")
        return "\n".join(lines)


def _short(v) -> str:
    if hasattr(v, "matlab_class") and getattr(v, "is_object", False):
        return f"[1×1 {v.matlab_class()}]"
    t = getattr(v, "text", None)
    if t is not None:
        return f"'{t}'"
    if getattr(v, "call", None) is not None and not hasattr(v, "backend_buffer"):
        return "[1×1 function_handle]"
    try:
        import numpy as np

        a = np.asarray(v.backend_buffer()).reshape(-1)
        if a.size == 1:
            return str(int(a[0])) if a.dtype == bool else f"{a[0]:g}"
    except Exception:
        pass
    return f"[1×1 {getattr(v, 'matlab_class', lambda: '?')()}]"


class EventData(_Obj):
    def __init__(self, source, name: str):
        self.source, self.name = source, name

    def matlab_class(self) -> str:
        return "event.EventData"

    def _props(self):
        from openmatlab.runtime.char_value import CharValue

        return {"Source": self.source, "EventName": CharValue(self.name)}


class Listener(_Obj):
    is_listener = True

    def __init__(self, source, name: str, callback):
        self.source, self.name, self.callback = source, name, callback
        self.enabled = True
        self.alive = True

    def matlab_class(self) -> str:
        return "event.listener"

    def _props(self):
        from openmatlab.runtime.char_value import CharValue

        return {"Source": self.source, "EventName": CharValue(self.name), "Callback": self.callback,
                "Enabled": _bool(self.enabled)}

    def get_prop(self, name: str):
        if not self.alive:
            raise _err("Invalid or deleted object.", "MATLAB:class:InvalidHandle")
        return super().get_prop(name)

    def set_prop(self, name: str, value):
        if not self.alive:
            raise _err("Invalid or deleted object.", "MATLAB:class:InvalidHandle")
        if name != "Enabled":
            if name in self._props():
                raise _err(f"Unable to set the '{name}' property of class 'event.listener' because it is read-only.",
                           "MATLAB:class:SetProhibited")
            raise _err(f"Unrecognized property '{name}' for class 'event.listener'.", "MATLAB:noPublicFieldForClass")
        import numpy as np

        self.enabled = bool(np.asarray(value.backend_buffer()).reshape(-1)[0])
        return self

    def delete(self):
        if self.alive:
            self.alive = False
            lst = _listeners(self.source)
            if self in lst:
                lst.remove(self)


def _listeners(src) -> list:
    lst = getattr(src, "_om_listeners", None)
    if lst is None:
        lst = []
        src._om_listeners = lst
    return lst


def _check_source(src, fn):
    if not cd.is_instance(src) or not src.info.is_handle:
        cls = src.matlab_class() if hasattr(src, "matlab_class") else type(src).__name__
        raise _err(f"Undefined function '{fn}' for input arguments of type '{cls}'.", "MATLAB:UndefinedFunction")
    src._check_alive()


def _check_event(src, name):
    if name not in event_names(src.info):
        raise _err(f"The name '{name}' is not an accessible event for class '{src.info.name}'.",
                   "MATLAB:class:EventNotFound")


def addlistener(args, *, nargout=1, attach=True):
    fn = "addlistener" if attach else "listener"
    if len(args) == 4:
        raise _err(f"{fn}: property events (PreSet/PostSet) are not supported yet.", "MATLAB:class:PropertyEvents")
    if len(args) != 3:
        raise _err("Not enough input arguments." if len(args) < 3 else "Too many input arguments.",
                   "MATLAB:narginchk")
    src, name, cb = args[0], _text(args[1], "Event name"), args[2]
    _check_source(src, fn)
    _check_event(src, name)
    if not callable(getattr(cb, "call", None)):
        raise _err("Listener callback must be a function handle.", "MATLAB:class:InvalidCallback")
    lh = Listener(src, name, cb)
    _listeners(src).append(lh)
    return (lh,)


def listener(args, *, nargout=1):
    return addlistener(args, nargout=nargout, attach=False)


def notify(args, *, nargout=0):
    if len(args) < 2:
        raise _err("Not enough input arguments.", "MATLAB:narginchk")
    src, name = args[0], _text(args[1], "Event name")
    _check_source(src, "notify")
    _check_event(src, name)
    data = args[2] if len(args) > 2 else EventData(src, name)
    if isinstance(data, EventData):
        data.source, data.name = src, name
    for lh in list(_listeners(src)):
        if lh.alive and lh.enabled:
            lh.callback.call([src, data], nargout=0)
    return ()


def event_data(args, *, nargout=1):
    return (EventData(None, ""),)


def drop(src) -> None:
    """The source was deleted: its listeners go with it."""
    for lh in list(getattr(src, "_om_listeners", None) or []):
        lh.alive = False
    if getattr(src, "_om_listeners", None):
        src._om_listeners.clear()
