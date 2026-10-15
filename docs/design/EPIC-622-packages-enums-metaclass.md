# EPIC-622: packages, import, enumerations and introspection (O-E5)

Criteria **O05** (`m8_o05_static_packages`), **O08** (`m8_o08_enumerations`) and **O09** (`m8_o09_introspection`) in [M8](../milestones/M8-object-system.md).

## Packages and import
- **Path lookup** (`libs/path.py`). A dotted name `pkg.sub.name` resolves to `+pkg/+sub/name.m` on each path entry. Empty segments are rejected.
- **Dotted calls** (`runtime/classdef_eval._static_chain`). When the root is a package folder, the whole chain is resolved as a package function or class constructor. Otherwise the chain is resolved as `Cls.static(...)`, `Cls.Const` or `Cls.Enum.prop`. A package-rooted name that resolves to nothing raises MATLAB's `Unable to resolve the name 'pkg.x'.`
- **import** (`runtime/imports.py`). Supports wildcard `import pkg.*` and single-name `import pkg.fn` / `import pkg.Cls`. Each evaluator (the base workspace, a script run in it, or one function call) keeps its own import list. An `ImportResolver` tries the imported names first. The exceptions: builtins stay ahead of wildcard imports, while an exact `import pkg.f` shadows them.
- **Static methods.** `methods (Static)` are callable as `Cls.m(...)` / `pkg.Cls.m(...)` and through `@Cls.m`.

## Enumerations (`runtime/enums.py`)
- Members are built once per class, in declaration order, and cached, so `Cls.M` is always the same member. A class derived from a numeric builtin (`< int32`) stores the underlying value. A class with properties gets its members from the constructor called with the declared arguments.
- Equality compares member identity. A numeric-derived member behaves as its value in relational and arithmetic operators and in conversions (`double`, `int32`, ...). `char`, `string` and `cellstr` return member names.
- `[A.x A.y]` builds an `EnumArray`. `size`, `numel` and indexing work on it, and it displays as `1×2 Cls enumeration array`.
- `switch` accepts a scalar enumeration member, and `case` matches by identity.
- `enumeration(C)` returns `[m, names]`. Called as a statement or in command form, it prints MATLAB's member listing. `isenum` is provided.
- Member properties cannot be set (`MATLAB:class:SetProhibited`).

## Introspection
- `properties` and `methods` (both print a listing as a statement), plus `ismethod`, `isprop`, `fieldnames` and `superclasses`, accept an instance or a class name, package-qualified names included.
- `metaclass(obj)` and `?Cls` give `Name`, `PropertyList`, `MethodList`, `SuperclassList` and `EnumerationMemberList`.
- Statement-form builtins in `math_builtins.STATEMENT_ZERO` now run inside `frames.calling`, so they see the caller's resolver.

## Adversarial review
Each probe below was run on the CLI.

| Probe | Result |
|---|---|
| `double(Lvl.High)` (a class reference used as a call argument) | Fixed. It used to fail because `struct_eval.expand` read `Lvl` as a value. Class-rooted unbound names now go through `eval_expr`. |
| `switch` on an enumeration member | Fixed. It used to raise "SWITCH expression must be a scalar". |
| `numel`/`size` of `EnumArray` | Fixed. It used to report 1×1. |
| `enumeration Col` / `methods('pkg.C')` as statements | Fixed. They used to show `ans =`, or error because no resolver was set. |
| `geo.nope(1)` | Fixed. It used to say "Undefined variable: geo". |
| `Col.Blue` (missing member), `c.foo = 1` | MATLAB-style errors. No traceback. |
| `Lvl.High + 1` | `int32` 11. |
| Existing tests and conformance expected files | Unchanged. The full suite passes. |

## Tests
- `tests/unit/test_classdef_packages_enums.py`
- `features/classdef_packages_enums.feature`
- conformance `m8_o05`, `m8_o08` and `m8_o09`

## Residuals
https://github.com/superche/openmatlab/issues/669
