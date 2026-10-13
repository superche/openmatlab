# EPIC-621: operators, indexing overloads and display (O-E4)

Criteria **O06** (`m8_o06_operator_overloading`) and **O07** (`m8_o07_subsref_subsasgn`), plus the display half of **O10**, in [M8](../milestones/M8-object-system.md).

## Operators (evaluator `_object_binop` / unary / transpose)
- **Binary operators.** When either operand is a class instance, the operator maps to its MATLAB method name: `plus minus mtimes times mrdivide rdivide mldivide ldivide mpower power eq ne lt le gt ge and or`.
  - The method is looked up on the arguments in order, so the left object wins. This is MATLAB's rule for operands of equal precedence; `InferiorClasses` is a residual.
  - With no overload, the existing handle `==`/`~=` identity applies, then a MATLAB "Operator 'op' is not supported" error.
- **Unary operators.** `-`, `+` and `~` map to `uminus`, `uplus` and `not`. `'` and `.'` map to `ctranspose` and `transpose`.
- **Concatenation.** `[...]` containing an object calls `horzcat` per row, then `vertcat` over the rows. Without those overloads, concatenating several objects is an error until object arrays arrive in O-E5.
- **Function handles.** `@Class.staticMethod` and `@pkg.fn` are parsed as dotted handles. A static method resolves through `_dotted_callable`.
- **Overloaded builtins.** Calls such as `double(obj)`, `char(obj)` and `length(obj)` already dispatched through the O-E1 method-name check.

## subsref / subsasgn (`runtime/classdef_subs.py`)
- An indexing expression rooted at a variable holding an instance whose class defines `subsref` is turned into the MATLAB substruct array `s` (`type`, `subs`). This covers `()`, `{}` and `.`, multi-level, with `:` as `':'` and `end` from an `end` overload, and the overload is called with nargout.
- Assignment statements (`ArrayAssign`/`CellAssign`/`ChainAssign`) call `subsasgn(obj, s, val)` and store the result. A handle class may return nothing.
- **Inside the class's own methods**, and its subclasses' (`_CTX`), built-in indexing is used, so overloads never recurse. This is MATLAB's rule.
- `builtin('subsref'|'subsasgn', ...)` runs default indexing through temporary names, reusing the evaluator's indexing and assignment.
- `builtin(name, ...)` calls the builtin table directly, bypassing overloads. `subsref`/`subsasgn`/`substruct` are also callable as plain functions.

## Display
When a variable is displayed and its class defines `display`, that method alone is called. If it defines only `disp`, the display is `name =` followed by a blank line and then `disp(obj)`. The default "with properties" display is unchanged.

## Tests
- `tests/unit/test_classdef_operators.py`
- `features/classdef_operators.feature`
- conformance `m8_o06` and `m8_o07`

## Residuals
https://github.com/superche/openmatlab/issues/653
