# #1085: unimplemented ode45/ode23 options error

`ode45` and `ode23` take an options structure as the fourth argument ([ode45](https://www.mathworks.com/help/matlab/ref/ode45.html), [ode23](https://www.mathworks.com/help/matlab/ref/ode23.html)). [odeset](https://www.mathworks.com/help/matlab/ref/odeset.html) stores the field list. This slice does not add Events, Mass, or stiff solvers (#1088, #1089, #1090). It stops the solver from ignoring a value it does not apply.

The public pages do not publish an identifier for “this solver has not implemented that option”, because MATLAB implements the options. The error id is therefore `OpenMATLAB:ode45:UnsupportedOption` or `OpenMATLAB:ode23:UnsupportedOption`. A fourth argument that is neither a structure nor empty is `OpenMATLAB:<solver>:OptionsNotStructure`.

## What the solver does with each accepted field

`odeset` still accepts every name below, including unique prefixes, and `odeget` still reads the stored value. The check runs in `ode45`/`ode23` before `f(t, y)` is called. `[]` is the placeholder `odeset` writes for an unset field.

| Field | When it is not an error | Otherwise |
|---|---|---|
| `RelTol`, `AbsTol`, `Refine`, `MaxStep`, `InitialStep` | one set value, or several case spellings that agree | spellings that disagree |
| `NormControl`, `Stats`, `BDF`, `Vectorized`, `JConstant` | every case spelling is `[]` or `'off'` / `"off"` | any other value |
| `Events`, `Mass`, `NonNegative`, `OutputFcn`, `OutputSel`, `Jacobian`, `JPattern`, `MaxOrder`, `MassSingular`, `MStateDependence`, `MvPattern`, `InitialSlope` | every case spelling is `[]` or blank text | any other value |

`'off'` is accepted only for those five switches. It is the path the solver already takes. No other unimplemented field has an off spelling: a set value is an error even when the text is `'off'` or `'no'`.

`Events` and `Mass` are reported before the other unimplemented fields when several are set. A function handle is never treated as empty.

Struct field names are case-sensitive, so `odeset` can leave canonical `Events` set to `[]` while `o.events` holds a function handle. Every field whose name matches the option, ignoring case, is read. An empty spelling does not hide another. Two set spellings of an applied option that differ raise `OpenMATLAB:<solver>:AmbiguousOption`.

## Shape of the options argument

The fourth argument must be one element, or empty. `[]`, any other empty non-structure, `struct()` with no fields, and a structure with `numel` 0 (including `o(:) = []`, which keeps the field names and drops every element) carry no values and mean no options. The solver does not index element 0 of an empty structure.

A structure with more than one element is `OpenMATLAB:<solver>:OptionsNotStructure`. The solver does not read the first element and leave a later `Mass` unused. This check runs before `f(t, y)`.

`MinStep` is not in the accepted list. `odeset('MinStep', ...)` is still `MATLAB:odeset:InvalidPropName`.

The fourth argument is the only options entry on the solver. Omitted, `[]`, or any other empty non-structure means no options. A nonempty non-structure (including a name/value pair placed on `ode45` itself) errors. `odeset` remains the place that builds the structure.

## What stays a success

A call that only sets applied options, or that leaves unimplemented fields empty, integrates as before. The five switches above may also be `'off'`. That includes `odeset()` with every field still `[]`, `odeset(old, 'Events', [])` after clearing a handle, a partial `struct('RelTol', ...)`, and one case spelling of an applied option beside an empty canonical field (`o.refine = 1` after `odeset()`).
