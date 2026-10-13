# Design: Epic #538, dense linear algebra decompositions (M7 C09)

Covers #560: eig, svd, lu, qr, chol, null, orth, trace, cross, dot (plus sqrtm).

## First principles
- **NumPy only** (`libs/decomp_builtins.py`), so there is no SciPy dependency. NumPy's LAPACK is the same family MATLAB uses.
- **eig.** Hermitian input uses `eigh` (real, ascending, as in MATLAB). Other input uses `dgeev`, whose order MATLAB does not guarantee. Eigenvectors are unit-norm columns. The third output gives left eigenvectors matched to the eigenvalue order. `'vector'` is supported. `eig(A,B)` uses `B\\A`. Integer and NaN/Inf input error with MATLAB IDs.
- **lu.** Gaussian elimination with partial pivoting: 1 output gives Y = L+U-I, 2 outputs give a permuted L, 3 outputs give P (or a vector).
- **chol.** It reads only the upper triangle (MATLAB) and reports the failure column `p` for the `[R,p]` form. Otherwise it errors with `MATLAB:posdef`.
- **qr.** Full or economy size. Three outputs do column pivoting.
- **null/orth.** Rank is found by SVD with MATLAB's default tolerance `max(size)*eps(max(s))`.
- **dot.** Conjugates its first argument (MATLAB).

## Existing-test change (user-approved, 2026-10-13)
`tests/conformance/scripts/m7_c09_linalg_decomp.m`: `e = eig(A)` became `e = sort(eig(A))`, and the expected value `[2;5]` is unchanged. MATLAB does not guarantee eigenvalue order for nonsymmetric input. Working through LAPACK's 2×2 step (dlanv2) for this matrix gives [5;2]. The original expected value was a guess written while the milestone was being set up.

## Adversarial review (done before PR)
| Attack | Result |
|---|---|
| Non-positive-definite `chol`, with 1 and 2 outputs | Error / `p`. Covered by a test. |
| Integer or NaN input to `eig` | MATLAB errors. Covered by a test. |
| Rectangular `lu`; economy `qr`/`svd` | Shapes match MATLAB. Covered by a test. |
| Complex `dot` | Conjugates. Covered by a test. |
| `cross` without a length-3 dimension; `trace` on a non-square matrix | Errors. Covered by a test. |
| Empty `svd` | 0x1. Probed. |

## Residuals
#598.
