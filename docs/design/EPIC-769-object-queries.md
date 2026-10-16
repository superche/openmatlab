# Epic #769 (M13 G-E2): graphics object queries

Milestone: [M13 Graphics completion](../milestones/M13-graphics.md), criterion G02 (and the last G07 check).

## Problem

There was no way to search the graphics tree: `findobj`, `findall`, `allchild`, `ancestor`, `groot` and `gco` were undefined, and `axes(f)` with a figure handle failed.

## Design

- New module `libs/graphics_query.py`. Traversal is depth-first, a parent before its children, with children in MATLAB `Children` order (newest first). A figure's legends are listed with the figure's children.
- `findobj([h,] [-depth d | 'flat'], expr)`: `expr` is a sequence of terms joined by `-and` (also the default between terms), `-or` or `-xor`. A term is `Name, Value`, `-regexp, Name, Pattern`, or `-property, Name`, optionally preceded by `-not`. Property names are case-insensitive. Text values compare exactly (`-regexp` uses a regular-expression search), and numeric values compare like `isequal`. No match gives a 0×1 empty handle array.
- `findobj` skips objects whose `HandleVisibility` is not `'on'`. `findall` includes them, and the axes title and label texts too.
- `allchild(h)` lists all children, hidden ones included (a cell array for several handles). `ancestor(h, type | {types}[, 'toplevel'])` returns `[]` when nothing matches. `groot` returns the root handle (`get(groot, 'CurrentFigure')` works). `gco` returns `[]` because there is no interactive selection.
- `axes(f)` creates axes in figure `f`. `axes(ax)` makes `ax` current.

## Adversarial review

| Attack | Result |
|---|---|
| `findobj(f, 'Tag')` (no value), `findobj(f, '-bogus', 1)`, an invalid regexp, `ancestor(l1)` | MATLAB-style errors, no traceback |
| Unknown property name in a query | No match (MATLAB behaviour), not an error |
| `findobj` on an empty handle | 0×1 empty |
| Hidden handles | Skipped by `findobj`, found by `findall` |
| `-depth 0`/`'flat'` on a handle array | Only the given objects are tested |
| Full test suite | Unchanged existing tests all pass |

Residual: `gco` has no current-object tracking (there are no mouse clicks in batch mode).
