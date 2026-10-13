# Design — Epic #496 linear solve `\` and `/`

## First principles
- **Operators follow the MATLAB docs (mldivide / mrdivide).** `A\B` with scalar `A`
  is elementwise `B./A`. Square `A` gets an LU solve with partial pivoting. Any
  other shape gets the least-squares solution. `B/A` is defined as `(A.'\B.').'`,
  so both operators share one solver (`numerics/linalg.py`). `.\` is
  `elem_div(right, left)`. Before this epic, matrix `/` silently divided
  element-wise (`[1 2;3 4]/[1 2;3 4]` returned all ones) and `\` raised
  "Unknown binary op".
- **NumPy only, with MATLAB-shaped failure modes.** The LU is our own Gaussian
  elimination, so an exactly singular matrix gives Inf/NaN plus a warning instead
  of an exception (as LAPACK does in MATLAB). `RCOND` is the 1-norm reciprocal
  condition estimate computed exactly as `1/(‖A‖₁‖A⁻¹‖₁)`.
- **Least squares returns the *basic* solution.** We use Householder QR with
  column pivoting and `tol = max(m,n)*eps*|R(1,1)|`, so at most `rank` entries
  are nonzero (`[1 2 3]\6 = [0;0;2]`, `ones(3,2)\[1;2;3] = [2;0]`). This differs
  from `pinv(A)*b`, as it does in MATLAB.
- **Warning channel.** `runtime/warnings.py` holds the minimal state.
  `warning(fmt, ...)` prints `Warning: msg` to stderr and sets `lastwarn`.
  `warning('off'|'on','all')` toggles printing, and `lastwarn` still records.

## Messages (MATLAB text)
| Case | Message |
|------|---------|
| exactly singular square | `Warning: Matrix is singular to working precision.` |
| rcond < eps | `Warning: Matrix is close to singular or badly scaled. Results may be inaccurate. RCOND = 1.000000e-17.` |
| rank-deficient non-square | `Warning: Rank deficient, rank = 1, tol = 1.153778e-15.` |
| row/column mismatch | error `Matrix dimensions must agree.` |
| non-scalar integer operand | error `Integer data types are not supported for matrix division; ...` |
| N-D operand | error `Arguments must be 2-D, or at least one argument must be scalar. ...` |

`inv` warns the same way; on a singular matrix it returns all `Inf`, as MATLAB does.
`det([])` is 1. `rank`/`pinv` use the SVD with `tol = max(size)*eps(max(s))`,
or a user-supplied tol. Results from `single` inputs are `single`, complex input
is supported, and a sparse operand returns a full result.

## Adversarial review (done before PR)
| Probe | Finding |
|-------|---------|
| `[1 2;3 4]/[1 2;3 4]` | `eye(2)` (was element-wise ones) ✓ |
| `1/[1 2]` | `Matrix dimensions must agree.` (MATLAB also errors) ✓ |
| `[2 0;0 4]\[2 4;4 8]` | multiple right-hand sides ✓ |
| `zeros(0,0)\zeros(0,1)` | `[](0x1)` ✓ |
| logical / char operands | promoted to double (`'ab'/2 = [48.5 49]`) ✓ |
| `int8(A)\b` | error ✓ (MATLAB allows scalar int only) |
| `{1}/2` | error as before ✓ |
| `[1i 0;0 2]\[1;1]` | `[-1i; 0.5]` ✓ |
| `norm`, `magic`, `cond`, `rcond`, `strncmp` | not implemented; filed as a residual |
| `warning('off', id)` | accepted silently; per-identifier state is a non-goal |

## Non-goals → residual issues
Per-identifier warning state and `warning` structs, warning identifiers, `norm/cond/rcond/magic`,
`linsolve` options, and the special solvers MATLAB picks for triangular/Hermitian matrices
(results are the same up to rounding). Sparse solvers live in #488.
