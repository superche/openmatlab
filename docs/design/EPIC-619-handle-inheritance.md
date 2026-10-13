# Design: Epic #619 (O-E2), handle classes and inheritance

M8 criteria **O02** (handle classes) and **O03** (inheritance). Builds on the class model from Epic #618.

## First principles

- **A handle is one Python object.**
  - `< handle`, or any handle ancestor, makes a class a handle class (`ClassInfo.is_handle`).
  - A property set mutates the shared record and returns the same object. Copies into variables, struct fields, cells and function arguments therefore all see the change, with no reference counting or aliasing table.
  - Value and handle superclasses cannot be mixed (`MATLAB:class:handleAndValue`).
- **Identity, not contents.**
  - `==`/`~=` on two handles compare identity. That is MATLAB's default `handle.eq`/`ne`, and a user `eq` method (O-E4) overrides it.
  - Comparing a handle with a non-handle is an error.
  - Value classes have no default `==`, as in MATLAB.
- **Lifetime is explicit.** `delete(h)` marks the object invalid and runs a user `delete` method if one exists (O-E7 extends this). Any later property access raises `MATLAB:class:InvalidHandle`, and `isvalid` reports it.
- **Inheritance is a method resolution order** (breadth-first over the superclass list).
  - Method lookup, property lookup and `isa` walk it.
  - A base-class method calling `area(obj)` dispatches on the runtime class, so the subclass override runs.
  - `meth@Super(obj, ...)` starts the lookup at `Super`.
- **Constructors chain.**
  - `obj@Super(args)` runs `Super`'s constructor on the object being built. The variable is updated, and the object keeps its subclass identity.
  - Any superclass without an explicit call is constructed implicitly with no arguments, before the subclass body (MATLAB).
- **Dispatch also covers late-loaded classes.** When a function name only exists as a method (`val(SubF())`), the arguments are evaluated and the method of the first object argument runs. If no object has the method, the original "Undefined function" error is kept.

## Adversarial review

| Attack | Result |
|---|---|
| Handle stored in a struct field and a cell, then mutated through each | One object. Covered by a unit test. |
| Linked handles (`a.next.val = 20`) | Nested chain assignment mutates `b`. Covered by a unit test. |
| `h == 5`; `==` on a value class | Errors (MATLAB). Covered by unit tests. |
| Use after `delete` | `MATLAB:class:InvalidHandle`. Covered by O02 and a unit test. |
| Implicit superclass constructor order | `B` before `M`. Covered by a unit test. |
| Dynamic dispatch from a base method; `meth@Super` chains | Covered by O03 and a unit test. |
| Mixing handle and value superclasses | `MATLAB:class:handleAndValue`. Covered by a unit test. |
| A method name used before its class loads (`val(SubF())`) | Dispatches. Covered by BDD. `foo(end)` still reports "Undefined function". |
| Graphics `delete(h)` and file `delete('f')` | Unchanged. Object arguments go to the handle-object delete. |

## Residuals

- Destructors on scope exit, and `delete` of objects held in containers: #624 (O-E7).
- Copyable `copy()`, `matlab.mixin.SetGet` behaviour, multiple-inheritance conflict detection: #636 (p2).
