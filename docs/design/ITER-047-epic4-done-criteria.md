# Feature `done` criteria — Epic #4 (#43) / Issue #47

Per PROCESS § Feature status criteria. Non-goals do **not** block `done`.

## libs.elmat_constructors → done
- Observable: `zeros/ones` (`()`, `(n)`, `(m,n)`), `eye` (`()`, `(n)`, `(m,n)`), `linspace(a,b[,n])` → 1×n
- Tests: `tests/unit/test_elmat_builtins.py`, `tests/bdd/test_elmat_bdd.py`
- Non-goals: vector size form `zeros([m n])`, class args, N-D

## libs.elmat_shape → done
- Observable: `size(A)`, `size(A,d)` (d>2 → 1), `[m,n]=size(A)`, `numel`, `length` (0 if empty)
- Tests: `tests/unit/test_elmat_builtins.py`
- Non-goals: N-D trailing-dims beyond 2

## libs.reductions → done
- Observable: `sum/prod/mean` default first non-singleton dim + `dim`; empty specials; `max/min` with `[m,i]` 1-based, `(A,B)`, `(A,[],dim)`
- Tests: `tests/unit/test_reductions.py`, `tests/bdd/test_reductions_bdd.py`
- Non-goals: MATLAB NaN-omit default for max/min, `'omitnan'`, `'all'`

## libs.elfun → done
- Observable: `abs sqrt exp log sin cos floor ceil round mod`, MATLAB `round` + `mod`, real-domain errors
- Tests: `tests/unit/test_elfun.py`, `tests/bdd/test_elfun_bdd.py`
- Non-goals: complex results, `rem/fix/atan2`
