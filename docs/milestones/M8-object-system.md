# M8 — Object system (classdef)

GitHub milestone: https://github.com/superche/openmatlab/milestone/8

**Related:**
- [M7 core language & I/O](M7-core-language-io.md) (closed): its object protocol for Map, datetime and graphics is the starting point.
- [`../GAP-ANALYSIS.md`](../GAP-ANALYSIS.md) (OOP row).
- [M3 Domain toolboxes](M3-domain-toolboxes.md) runs interleaved.

## Intent

MATLAB `classdef` OOP, implemented clean-room from public MATLAB documentation. The milestone covers:
- value and handle classes;
- properties with attributes, and methods;
- constructors and inheritance;
- packages, enumerations, operator and indexing overloads, introspection and display;
- the existing built-in objects (graphics handles, datetime, containers.Map) moved onto the same model.

This scope, the exit criteria and the ordering were approved on 2026-10-13.

## Exit criteria (measurable)

M8 is **done** only when **all** of these hold on `main`:

1. **Conformance.** Every criterion in [`tests/conformance/m8_manifest.py`](../../tests/conformance/m8_manifest.py) is `met`, and `pytest tests/conformance/test_m8_conformance.py` reports **0 xfail**.
2. **No open `p0` issue** on milestone/8.
3. **No Python traceback.** No Python exception reaches the user, checked by a probe sweep over the class features (same method as the M7 close-readiness sweep).
4. **Docs.** No doc drift; CI on `main` is green; each epic has an acceptance package (`docs/acceptance/EPIC-NNN.md`) accepted by the user.

Pending scripts run as **strict xfail** and flip to `met` in the PR that makes them pass. The scripts are thick: each writes real class files into a `tempname` folder on the path and checks between 8 and 20 values.

## Criteria

| # | Criterion | Script | Priority | Epic | Status |
|---|-----------|--------|----------|------|--------|
| O01 | Value classes: properties with defaults, constructor with `nargin`, methods called as `f(obj)` and `obj.f()`, multiple outputs, copy-on-assign, unknown property errors, `isequal`/`class`/`isa`/`isobject` | m8_o01_value_class | p0 | #618 | met (Epic #618; residual #620) |
| O02 | Handle classes: reference semantics through copies and function calls, `==`/`~=` identity, `isvalid`/`delete`, error on a deleted handle | m8_o02_handle_class | p0 | #619 | met (Epic #619; residual #636) |
| O03 | Inheritance: multilevel, `obj@Super(...)`, `method@Super(obj)`, dynamic dispatch from base methods, `superclasses`, handle subclasses | m8_o03_inheritance | p0 | #619 | met (Epic #619; residual #636) |
| O04 | Property attributes: `Constant`, `Dependent` with `get.`/`set.` methods, `SetAccess`/`Access = private`, a validating setter, a setter not re-entered while it sets its own property | m8_o04_property_attributes | p1 | #620 | met (delivered with Epic #618; validation residual #620) |
| O05 | `Static` methods, `+package` functions and classes, `import pkg.*` | m8_o05_static_packages | p1 | #622 | met (Epic #622; residual #669) |
| O06 | Operator overloading (either operand an object), `horzcat`, conversion (`double`/`char`), overloaded builtins | m8_o06_operator_overloading | p1 | #621 | met (Epic #621; residual #653) |
| O07 | `subsref`/`subsasgn` overloads with `builtin()` fallback, multi-level indexing, no recursion inside methods | m8_o07_subsref_subsasgn | p1 | #621 | met (Epic #621; residual #653) |
| O08 | Enumerations: plain, integer-based (`< int32`), with properties and a constructor; `enumeration()`, `switch`, arrays | m8_o08_enumerations | p1 | #622 | met (Epic #622; residual #669) |
| O09 | Introspection: `properties`, `methods`, `ismethod`, `isprop`, `fieldnames`, `metaclass`, `?Class`, `which` | m8_o09_introspection | p1 | #622 | met (Epic #622; residual #669) |
| O10 | Display (default "with properties", `disp` overload) and dot notation on built-in objects (graphics `h.Prop`, `datetime` `.Year`) | m8_o10_display_dot_objects | p1 | #621, #623 (#593, #602) | met (Epics #621, #623; residual #673) |

## Epics (approved order)

1. **O-E1 #618 (p0):** class model, parsing and loading, value classes. Covers O01.
2. **O-E2 #619 (p0):** handle classes and inheritance. Covers O02 and O03.
3. **O-E3 #620 (p1):** property attributes. Covers O04, which was already met through O-E1. O-E3 adds property validation (`(dims) Class {validators}`), the `mustBe*` validators, Abstract classes, immutable and Hidden ([design](../design/EPIC-620-property-validation.md); residual #645). Interleaved with M3 E1–E5.
4. **O-E4 #621 (p1):** operators, indexing overloads and display. Covers O06, O07 and the display half of O10. Interleaved with M3 E1–E5.
5. **O-E5 #622 (p1):** packages, static methods, enumerations and introspection. Covers O05, O08 and O09.
6. **O-E6 #623 (p1):** built-in objects on the class model. Covers the dot-notation half of O10.
7. **O-E7 #624 (p2):** events and listeners, destructors, objects in MAT files. Not an exit criterion; covered by unit and BDD tests.

## Risks and design questions

- **Handle identity and lifetime:** explicit `delete` versus Python GC.
- **Value-object copy cost:** copy-on-write versus deep copies.
- **Dispatch precedence:** methods versus path functions, mixed-class operators, `InferiorClasses`.
- **Indexing overloads:** `subsref`/`subsasgn` cost and recursion rules; built-in indexing inside methods.
- **Class reloading:** a class file edited while instances exist.
- **Migration:** moving Map, datetime and graphics onto the model must not regress M7 tests. Any change to an existing test follows the stop-and-ask rule.

## Progress snapshot

M8 opened 2026-10-13.

**10 / 10** criteria met: O01 (Epic #618), O04 (Epic #618, from the same class model), O02 (Epic #619), O03 (Epic #619), O06 (Epic #621), O07 (Epic #621), O05, O08, O09 (Epic #622), O10 (Epics #621 + #623). O-E7 events/listeners, destructors and objects in MAT files (#624, p2, no exit criterion) delivered; residual #677.


## Close-out (2026-10-16)

**Status: closed.** Shaw accepted every epic (#618–#624) on 2026-10-16 (Asia/Shanghai), and the GitHub milestone is closed.

- **Criteria:** 10 / 10 met (O01–O10), with 0 xfails on `main`.
- **Open p0 issues:** none (epics #618/#619 closed after acceptance).
- **Doc drift:** the drift test passes.
- **`main` CI:** green.

**Residuals left on closed milestone/8** (p2; not re-homed):

| Issue | Pri | Topic |
|---|---|---|
| #593 | p2 | Graphics residual (dot-notation breadth, 3-D, colormap, …) |
| #602 | p2 | Map/datetime residual (time zones, calendarDuration, NaT, …) |
| #636 | p2 | Handle/inheritance residual (Copyable, SetGet, MI conflicts, Sealed/Abstract) |
| #645 | p2 | O-E3 residual (arguments blocks, more mustBe*, user-class conversion) |
| #653 | p2 | O-E4 residual (InferiorClasses, numel/size + subsref nargout, cell display) |
| #669 | p2 | O-E5 residual (import validation, enum by name, metaclass fidelity, object arrays) |
| #673 | p2 | O-E6 residual (graphics class names/display, handle arrays, datetime assignment) |
| #677 | p2 | O-E7 residual (property events, EventData, destructor on clear, saveobj/loadobj) |
