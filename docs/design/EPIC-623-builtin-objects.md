# EPIC-623: built-in objects on the class model (O-E6)

Graphics/datetime half of criterion **O10** (`m8_o10_display_dot_objects`) in [M8](../milestones/M8-object-system.md). The display half was delivered by O-E4 (#621).

## Graphics handles (`libs/graphics_builtins.GraphicsHandle`)
- Scalar handles returned by graphics functions (`figure`, `gcf`, `gca`, `plot`, ...) are a `GraphicsHandle`. It subclasses the numeric `NDArrayValue` and carries the session's handle model. The numeric id is unchanged, so `get`/`set`, `==`, `ishandle` and arithmetic behave as before, and arithmetic results are plain `double`.
- `h.Prop` reads through the same `_get_prop` as `get`. `h.Prop = v` writes through `_set_prop` as `set` does, with the same validation, read-only checks, autoscaling and re-render. `set_prop` returns the same handle, which gives handle semantics: `k = h; k.LineWidth = 5` changes `h` too.
- `ax.XLim(2)` indexes the property value.
- Once the object is deleted (`close`/`delete`), `h.Prop` raises `Invalid or deleted object.` `isvalid(h)` returns false and `isobject(h)` returns true.
- The model is attached by the intrinsic wrapper (`_wrap`), so `_h` call sites did not change. A handle made outside an intrinsic call stays a plain double.
- Dot reads accept `is_graphics_handle` in `struct_eval.read_field`, `Evaluator._object_base` and `classdef_subs._field`. Dot writes go through the existing `set_prop` branch of `struct_eval._assign`.

## datetime / containers.Map
`dt.Year`/`.Month`/`.Day` and `m.Count` already go through the object `get_prop` path. Conformance now covers them.

## Adversarial review
Each probe below was run on the CLI.

| Probe | Result |
|---|---|
| `h.Nope` | `Unrecognized property Nope for class Line.` |
| `h.Type = 'x'` | read-only error |
| `h.LineWidth = -1` | validation error, same as `set` |
| `close(f); h.LineWidth` | `Invalid or deleted object.` No traceback. |
| `h2 = h; h2.LineWidth = 5; h.LineWidth` | 5 (handle semantics) |
| `h + 0 == h` | 1. The result is a plain double. |
| `ax.XLim(2)` | Fixed. It used to raise "Unrecognized method 'XLim' for class 'double'". |
| `s.h = h; s.h.LineWidth` | works |
| `h(1).LineWidth` on a handle array | not supported (residual #673) |
| `x = 5; x.a` | unchanged MATLAB error |

No existing test or conformance expected file changed. The full suite passes.

## Tests
- `tests/unit/test_graphics_dot_objects.py`
- `features/graphics_dot_objects.feature`
- conformance `m8_o10_display_dot_objects` (now met)

## Residuals
https://github.com/superche/openmatlab/issues/673
