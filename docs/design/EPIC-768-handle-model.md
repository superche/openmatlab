# Epic #768 (M13 G-E1): graphics handle model upgrade

Milestone: [M13 Graphics completion](../milestones/M13-graphics.md), criterion G01. Absorbs the graphics part of #673.

## Problem

Graphics handles were plain doubles. Only a scalar returned straight from a graphics builtin carried the model (`GraphicsHandle`, O-E6), so `h(k)`, `[h1 h2]`, `h'`, `for g = h`, `ax.Children` and handle arrays from `plot` with several columns all fell back to numbers. `class(h)` said `double`, there was no `h(k).Prop = v`, and `isvalid` failed on arrays.

## Design

- `GraphicsHandle` (in `libs/graphics_builtins.py`) is an N-d array of handle ids that knows its `Model`. The buffer is still the numeric ids, so `get`/`set`, `==`, `isequal`, arithmetic and `double(h)` keep the numeric behaviour (`double(h)` and `h + 0` return plain doubles).
- `matlab_class()` returns the full MATLAB class name: `matlab.ui.Figure`, `matlab.graphics.axis.Axes`, `matlab.graphics.chart.primitive.Line|Bar|Scatter|Histogram`, `matlab.graphics.primitive.Text`, `matlab.graphics.illustration.Legend`. Mixed arrays are `matlab.graphics.Graphics`, and `gobjects` placeholders are `matlab.graphics.GraphicsPlaceholder` (approved default: `class(h)` returns the full name). `isa(h, 'handle')`, `isa(h, 'matlab.graphics.Graphics')` and `isa(h, <own class>)` are true, and `isnumeric(h)` is false.
- Handle arrays stay handle arrays through paren indexing (including `end` and `:`), transpose, `[ ]` concatenation where every non-empty part is a handle, `h(k) = g` growth, `h(k) = []` deletion, `for` loop columns, `arrayfun` elements, and `Children`/`Parent` reads through dot notation. An assignment that would put numbers that are not handles into the array leaves a plain double.
- Dot access: `h.Prop` on a scalar reads the property. On an array it returns a cs-list, so `[h.Prop]` and `{h.Prop}` work. `h(k).Prop = v` and `h(k).Prop(i) = v` write through the model. `h.Prop = v` on a non-scalar array raises `Scalar object required for this assignment` (use `set(h, ...)`).
- `isvalid(h)` and `isgraphics(h)` are element-wise. `delete(h)` on an array skips elements that are already deleted and placeholders, and `gobjects(n)` / `gobjects(m,n)` create placeholder arrays (NaN ids).
- Display: a scalar shows `  Line with properties:` and the short property list MATLAB shows for that type, then `Show all properties`. An array shows `  2×1 Line array:` and one line per element. A deleted handle shows `handle to deleted Line`.

## Adversarial review

| Attack | Result |
|---|---|
| `h(5)` out of range, `h(1.5)`, `h{1}` | MATLAB errors, no traceback |
| `h(1).Nope`, `h(1).Nope = 3` | `Unrecognized property Nope for class Line.` |
| Reading and writing a deleted handle | `Invalid or deleted object.`; display says `handle to deleted Line` |
| `h(1) = 7` (a number that is not a handle) | Result is a plain double, not a broken handle array |
| `[gca; h]` | `matlab.graphics.Graphics` array |
| `h.LineWidth = 2` on a 2×1 array | Scalar-object error, no partial write |
| `delete(h)` twice, `delete(gobjects(2))` | No-op |
| `x = h; x(1).LineWidth = 7` | Handle semantics: `h(1).LineWidth` is 7 too |
| A probe sweep of 47 odd expressions (`h*2`, `sort(h)`, `unique(h)`, `repmat`, `properties(h)`, `num2str(h)`, ...) | No Python traceback |
| Full test suite | Unchanged existing tests all pass |

Residuals: `properties(h)`/`methods(h)` do not list graphics properties yet, and `get(h)` with no name on an array is still an error (MATLAB returns a struct array). Both are filed as an issue.
