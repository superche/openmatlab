# Design: Epic #618 (O-E1), classdef core: class model, parsing, value classes

M8 criterion **O01**. Property attributes (**O04**) come out of the same class model, so they are met in the same PR (see the note in the table below).

## First principles

- **A class is a container of ordinary functions.** `lang/classdef_parser.py` keeps the file's structure:
  - the header (attributes, superclasses);
  - `properties`, `methods`, `events` and `enumeration` blocks, each with its attributes;
  - local functions after the closing `end`.

  It reuses the statement parser for method bodies and the expression parser for property defaults. Methods are plain `MFileCallable`s, so `nargin`, `varargout`, local functions and errors behave exactly as in function files.
- **An instance is a record of property values plus its class** (`runtime/classdef.py`, `ClassInstance`).
  - Value objects copy on write: a property set returns a new instance, so `b = a; b.x = 9` never changes `a`, and sharing a Python object between variables is safe.
  - Handle objects mutate in place; that is O-E2.
- **Constructors.** The output variable is pre-bound to the default object, as in MATLAB. Superclass constructors run implicitly with no arguments unless the body calls `obj@Super(...)`.
- **Dispatch is by argument.** `f(obj, ...)` runs `obj`'s method `f` ahead of path functions and builtins. `obj.f(...)` is the same call. The evaluator only checks for this when the name matches a method of a loaded class, so ordinary calls are unchanged and their arguments are still evaluated once.
- **Access is checked against the running method's class.** A ContextVar stack is pushed by every method call. `get.`/`set.` accessors are not re-entered for the same object and property, so `obj.c = v` inside `set.c` stores directly (MATLAB).
- **The evaluator integration is narrow.**
  - `runtime/classdef_eval.py` resolves dotted targets: `obj.p`, `obj.m(...)`, `Cls.Static(...)`, `Cls.Const`, and `pkg.fn` (the last ready for O-E5).
  - It returns `None` for anything that is not class-related (structs, `containers.Map`), so existing paths are untouched.
  - Assignment chains (`obj.p = v`, `obj.p(3) = v`) go through one new step in `struct_eval._assign`.

## Language prerequisites found on the way

The thick O-scripts write class files with cell literals that span lines. Two gaps were fixed in the core language:
- `...` line continuation (MATLAB ignores the rest of the line);
- a trailing comma before `]`/`}`/`;` in literals.

`?Name` (meta-class) and `obj@Super` / `meth@Super` are now parsed. They are evaluated in O-E2 and O-E5.

## Adversarial review

| Attack | Result |
|---|---|
| `b = a; b.x = 9` changes `a` | No. A new instance is created on write. Covered by unit test and O01. |
| A bare class name `p = Pt;` is read as a script | No. `load_mfile` returns a `ClassFile` marker. Covered by unit test. |
| A file name differs from the class name | MATLAB error ("must match"). Covered by unit test. |
| Too many constructor arguments, unknown property get/set | `MATLAB:TooManyInputs`, `MATLAB:noSuchMethodOrField`, `MATLAB:noPublicFieldForClass`. Covered by unit test and O01. |
| A size/class spec in a property line (`y (1,1) double = 2`) | Parsed and accepted; not yet enforced (#620). |
| A setter that sets its own property recurses | No. It is guarded per object and property. Covered by O04. |
| Private or `SetAccess = private` access from outside | `MATLAB:class:GetProhibited` / `SetProhibited`. Covered by O04 and unit test. |
| Local functions in a class file | Visible to the methods only. Covered by unit test. |
| Existing struct and `containers.Map` dot paths | Unchanged. The full suite stays green and no existing test changed. |

## Residuals

- Property validation (size/class/validator functions), `Abstract`/`Hidden`/`immutable` semantics: #620 (O-E3).
- Object arrays: #622 (O-E5, enumeration arrays).
- Operators: #621 (O-E4).
