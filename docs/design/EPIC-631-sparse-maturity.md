# EPIC-631: Sparse maturity (M3-E7)

Criterion **T07** (`m3_t07_sparse`) in [M3](../milestones/M3-domain-toolboxes.md). Ships in **core**. Child: #527.

## First principles
- Sparse is still an attribute over CSC `Store` (Epics #487 / #520). Mostly-true logical results (`~S`, `S == 0`, `S <= k`) are sparse in MATLAB; materialising their true entries is O(m·n) and is only done when `m*n ≤ COMPLEMENT_BUDGET` (10⁷). Larger cases fall back to densify (same hard limit as before).
- `kron(A,B)` is sparse whenever either factor is sparse. The product is built from the Cartesian product of nonzeros: `(i,j,va)×(r,c,vb) → (i·mb+r, j·nb+c, va·vb)`.
- Sparse `\` already stays compressed for the well-conditioned patterns covered by #522; T07 checks a tridiagonal n=2000 solve without densifying `T`.

## Scope delivered
| Case | Behaviour |
|---|---|
| `~S` | Sparse logical complement of truthy entries |
| `S == 0`, `S <= k`, and other `S op k` with `op(0,k)` true | Sparse logical: true everywhere except failing stored entries |
| `S op k` with `op(0,k)` false | Unchanged (true only at matching nonzeros) |
| `kron(S,T)` / `kron(S,F)` / `kron(F,S)` | Sparse |
| `S*k`, `S+S`, `S'`, `sum`, indexing, `spones`/`spalloc`/`spdiags` | Already sparse from prior epics |
| `A\b` (full rhs), n=2000 tridiagonal | Full result, accurate; `T` stays sparse |

## Adversarial review
| Probe | Result |
|---|---|
| Conformance T07 expected JSON | All 20 checks match |
| `~speye(3)` | nnz 6, diagonal false |
| `speye(3) == 0` | Same pattern as `~` |
| `kron(speye(2), sparse([4 1 0;1 4 1;0 1 4]))` | Sparse 6×6 |
| `kron([1 2],[1;1])` (full×full) | Unchanged dense path |
| n=2000 `spdiags` tridiagonal `\` | `yy(1000) ≈ 1/6`, nnz(T)=5998, no densify of T |
| `m*n > COMPLEMENT_BUDGET` for `~S` / `S==0` | Returns to dense path (residual: true complement form) |
| Existing #522/#523 unit suites | Still green |

No existing test or conformance expected file changed.

## Residuals
https://github.com/superche/openmatlab/issues/685
