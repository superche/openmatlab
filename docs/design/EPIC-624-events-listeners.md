# EPIC-624: events, listeners, destructors, objects in MAT files (O-E7)

[M8](../milestones/M8-object-system.md) epic O-E7 (p2). It is not an exit criterion, so it is tracked by unit and BDD tests.

## Events and listeners (`runtime/events.py`)
- Event names come from the `events` blocks of the class and its superclasses.
- `addlistener(src, 'Evt', @cb)` and `listener(...)` return an `event.listener` with `Source`, `EventName`, `Callback` and a settable `Enabled`. Only handle-class sources are accepted. An unknown event raises `The name 'X' is not an accessible event for class 'C'.`
- `notify(src, 'Evt')` calls each enabled listener as `cb(src, evt)`, in the order they were added. `evt` is an `event.EventData` with `Source` and `EventName`.
- Method forms `obj.addlistener(...)`, `obj.notify(...)`, `obj.delete` and `obj.isvalid` fall back to the handle builtins in `classdef.dot_access`.
- `delete(lh)` removes the listener, and `isvalid(lh)` then returns false. When the source is deleted, its listeners become invalid too.

## Destructors
`delete(obj)` on a handle object runs the user `delete` method once (O-E1 already did this) and now also drops the object's listeners.

## Objects in MAT files (`libs/mat5.py`, `file_builtins._revive`)
- `save` writes a classdef instance as a v5 `mxOBJECT` element: the class name plus a struct of its stored (non-Constant, non-Dependent) properties. This is the documented v5 object layout.
- The reader keeps the class name on the struct. `load` rebuilds an instance when the class is on the path. As in MATLAB, the constructor is not called: the instance starts from the class defaults, the saved values are applied, and objects nested in object properties are rebuilt the same way. If the class is missing, MATLAB's warning is shown and the value loads as a struct.
- Enumeration members and deleted handles raise MATLAB-style `save` errors.

## Adversarial review
Each probe below was run on the CLI.

| Probe | Result |
|---|---|
| `addlistener(a, 'Nope', cb)` | MATLAB error, no traceback |
| `notify(5, 'x')` | `Undefined function 'notify' for input arguments of type 'double'.` |
| `lh.Enabled = false` | notify skips the listener. Setting `lh.Source` raises a read-only error. |
| `delete(a)` while a listener exists | destructor prints, `isvalid(lh)` is 0 |
| save, `clear`, `load`; `s = load(f)` | class and values restored |
| load without the class on the path | warning, then a struct |
| Unit tests calling `cd` | Removed, because `cd` leaked the process cwd into later tests. Tests use absolute paths. |

No existing test or conformance expected file changed. The full suite passes.

## Tests
- `tests/unit/test_classdef_events.py`
- `features/classdef_events.feature`

## Residuals
https://github.com/superche/openmatlab/issues/677
