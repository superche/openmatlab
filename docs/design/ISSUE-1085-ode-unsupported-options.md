# #1085: unimplemented ode45/ode23 options error

`ode45` and `ode23` take an options structure as the fourth argument ([ode45](https://www.mathworks.com/help/matlab/ref/ode45.html), [ode23](https://www.mathworks.com/help/matlab/ref/ode23.html)). [odeset](https://www.mathworks.com/help/matlab/ref/odeset.html) stores the field list. This slice does not add Events, Mass, or stiff solvers (#1088, #1089, #1090). It stops the solver from ignoring a value it does not apply.

The public pages do not publish an identifier for “this solver has not implemented that option”, because MATLAB implements the options. The error id is therefore `OpenMATLAB:ode45:UnsupportedOption` or `OpenMATLAB:ode23:UnsupportedOption`. A fourth argument that is neither a structure nor empty is `OpenMATLAB:<solver>:OptionsNotStructure`.

## What the solver does with each accepted field

`odeset` still accepts every name below, including unique prefixes, and `odeget` still reads the stored value. The check runs in `ode45`/`ode23` before `f(t, y)` is called. `[]` is the placeholder `odeset` writes for an unset field.

| Field | When it is not an error | Otherwise |
|---|---|---|
| `RelTol`, `AbsTol`, `Refine`, `MaxStep`, `InitialStep` | always (these are applied) | — |
| `NormControl`, `Stats`, `BDF`, `Vectorized`, `JConstant` | `[]` or `'off'` / `"off"` (the path already taken) | error |
| `Events`, `Mass`, `NonNegative`, `OutputFcn`, `OutputSel`, `Jacobian`, `JPattern`, `MaxOrder`, `MassSingular`, `MStateDependence`, `MvPattern`, `InitialSlope` | `[]` or blank text | error |

`Events` and `Mass` are reported before the other unimplemented fields when several are set. A function handle is never treated as empty.

`MinStep` is not in the accepted list. `odeset('MinStep', ...)` is still `MATLAB:odeset:InvalidPropName`.

The fourth argument is the only options entry on the solver. Omitted, `[]`, or any other empty non-structure means no options. A nonempty non-structure (including a name/value pair placed on `ode45` itself) errors. `odeset` remains the place that builds the structure.

## What stays a success

A call that only sets applied options, or that leaves unimplemented fields empty or `'off'`, integrates as before. That includes `odeset()` with every field still `[]`, `odeset(old, 'Events', [])` after clearing a handle, and a partial `struct('RelTol', ...)`.
