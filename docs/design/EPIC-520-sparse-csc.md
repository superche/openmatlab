# Design — Epic #520 compressed sparse storage (CSC)

Covers #515 (container, construction, queries), #516 (kernels) and #517
(indexing, assignment, concatenation). Split from #501. NumPy only, no SciPy.

## First principles
- **One payload, CSC order.** `numerics/sparse_store.py` `Store` keeps the
  nonzeros of an m×n matrix as three flat arrays: `rows` (row index), `cols`
  and `data`. They are sorted column-major (column, then row), hold no
  duplicates and no explicit zeros. That ordering is CSC: `indptr` (column
  pointers) comes from `searchsorted(cols, 0..n)` when a kernel needs it.
  Memory is O(nnz) and nothing allocates m*n. The store is immutable, so every
  operation returns a new store.
- **SparseValue stays an NDArrayValue.** `SparseValue(NDArrayValue)` now has
  `__slots__ = ("store",)`. `shape`, `numel`, `ndim` and `matlab_class` read the
  store. `backend_buffer()` materialises a dense copy lazily, caches it and
  increments `sparse.DENSIFY_COUNT`. Every consumer that predates this epic
  therefore behaves exactly as before. Tests assert a zero densify delta on the
  native paths.
- **Native first, dense fallback.** The backend `_sparse_aware` wrapper calls
  `sparse.native_op` before the dense method, covering matmul, `_elem`, power,
  transpose, index and set_index. Zero-preserving builtins (`_keep_sparse`)
  call `native_sparse_call`, and `find`, `size`, display and concatenation
  read the store. Any case a kernel cannot reproduce exactly returns `None` and
  takes the old dense path plus the sparsity rules, so results never diverge.
- **IEEE guard.** `0*Inf` and `0/0` are NaN, so `S*Inf`, `S.*F` with a
  non-finite `F`, `S./F` with a zero in `F`, and `S*x` with a non-finite `x` take
  the dense path. `max`/`min` with NaN data and complex `max`/`min` do as well.
  `sqrt`/`asin`/`atanh` go native only on their real domain.

## Native coverage
| Area | Native |
|------|--------|
| construction (#515) | `sparse(A)`, `sparse(m,n)`, `sparse(i,j,v[,m,n])` (duplicates add; logical ORs), `speye`, `spalloc`, `spdiags` (create and extract), `sprand(m,n,d)` / `sprand(S)`, `spones`, `spfun` |
| queries (#515) | `nnz`, `nzmax`, `nonzeros`, `find` (1–3 outputs), `size`/`numel`/`isempty`, `full`, `issparse`, `class`, triplet display |
| kernels (#516) | `S*X`, `X*S` (full results), `S*S` (expand and coalesce), `S±S`, `S.*S`, `S.*X`, `X.*S`, `S./X`, `k*S`, `S*k`, `-S`, `S'`, `S.'`, `S.^p` (p>0), `abs sqrt sin tan sinh tanh asin atan asinh atanh floor ceil round fix real imag conj double logical`, `sum(S[,dim])`, `max/min(S)`, `max/min(S,[],dim)` |
| indexing (#517) | `S(i,j)` (with repeats), `S(k)`, `S(mask)`, `S(:)` (now sparse, as in MATLAB), `S(i,j)=v`, `S(k)=v`, growth, `S(i,:)=[]`, `S(:,j)=[]`, `S(k)=[]`, `[S F; F S]` |
| dense fallback | relational ops whose result is mostly true (`S == 0`, `S <= 1`, `~S`), singular or ill-conditioned `S\b` (the dense path issues the MATLAB warnings), class-changing assignment (logical ↔ double) |

## Adversarial review (done before PR)
| Probe | Finding |
|-------|---------|
| `sparse(1e5,1e5)`, `speye(1e5)`, `nnz`, display | zero densify ✓ |
| `max(-speye(3))` | the implicit zeros take part, giving 0 ✓; for `max(-A)` over a full column of negatives the result is the negative max ✓ |
| `S*Inf`, `S.*[Inf 1;1 1]`, `S./0` | NaN where `0*Inf` or `0/0` occur (dense path) ✓ |
| `sqrt(sparse(-4))` | complex result through the dense path ✓ |
| `round(S/3)` | half away from zero (not NumPy banker's rounding) ✓ |
| `S(:)` | used to return full through the generic reshape; it is now sparse, as in MATLAB (no existing test asserted the old class) |
| `S(4,1)` on 3×3, `S(0)`, size-mismatched assignment | same errors as the dense path, raised without densifying ✓ |
| `S(n, n+5) = 1` on 1e5×1e5 | grows the columns natively ✓ |
| `[S; S]` with 1e5 rows | native concat ✓ |
| `S\b` | densifies (allowed by #517); a native sparse direct solve is a residual |
| linear `S(:)` on a 1e5×1e5 matrix | the evaluator expands `:` to `1:numel` (1e10 indices) before indexing; residual |

## Follow-ups #522 and #523 (native solve, remaining paths)
- **`S\b` and `b/S` (#522)** are handled in `numerics/sparse_solve.py`, reached from `linalg_builtins.solve` when `S` is sparse and `b` is full. The cheapest applicable method wins:
  1. diagonal;
  2. lower or upper triangular, by column substitution;
  3. banded, by LU with partial pivoting in a sliding (kl+1)×(2kl+ku+1) window, at O(n·kl·(kl+ku)) work;
  4. general patterns: reverse Cuthill–McKee reordering first, then the banded solver, provided the permuted bandwidth fits a work budget (4e8).
  - A zero pivot, or a min/max pivot ratio below eps, returns to the dense solver so that MATLAB's singular and RCOND warnings stay exact. So does `S\S`. The result is full, as in MATLAB.
- **Remaining paths (#523):**
  - `S(:)` is reshaped straight from the store; `:` is no longer expanded to `1:numel`.
  - Relational ops `S op k`, `k op S` and `S op S` stay native whenever `op(0,0)` is false.
  - Native builtins: `mean`, `cumsum` (per-column fill-in), `reshape`, `flip`/`flipud`/`fliplr`, `circshift`, `permute([1 2]|[2 1])`.
  - `S^p` for integer p ≥ 1 uses repeated squaring.
  - `for c = S` slices the columns from the store.
- **Review:**
  - `E == 2*E` on a 1e5×1e5 matrix is mostly true. MATLAB stores that as about 1e10 nonzeros, which cannot fit in bounded memory, so it takes the dense path.
  - `cumsum(speye(n))` really has n(n+1)/2 nonzeros. Its cost is inherent, not a densify.
  - A large singular `S\b` densifies (residual).
