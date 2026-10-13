# Design — Epic #487 sparse matrices

## First principles
- **Sparse is an attribute, not a new number type.** `SparseValue` subclasses
  `NDArrayValue` (`numerics/sparse.py`), so every numeric path, plus `size`,
  `find` and `isequal`, works unchanged. The class stays `double`/`logical`, as
  in MATLAB.
- **NumPy only.** The project has no SciPy dependency, so the buffer is dense.
  Behaviour matches MATLAB, but memory is O(m*n). Compressed storage is filed
  as residual #488.
- **One place for the propagation rules.** `sparse_result(kind, out, a, b, op)`
  wraps the backend ops `matmul`, `_elem`, `power`, `transpose`, `index` and
  `set_index`, layered like the `single` rules. Concatenation, relational ops
  and unary minus call it in the evaluator. Zero-preserving builtins use
  `_keep_sparse`.

## Rules (MATLAB)
| Case | Result |
|------|--------|
| `S+S`, `S-S`, `S*S`, `S*k`, `k*S` | sparse |
| `S+k`, `S*F`, `F*S` | full |
| `S.*X`, `X.*S`, `S./X` | sparse; `X./S` is full |
| `S.^p` with p>0, `S^p` | sparse |
| `S'`, `-S`, `S(i,j)`, `S(i,j)=v`, `[S F]`, `S>0` | sparse |
| `abs/sqrt/sin/floor/ceil/round/fix/real/imag/conj/sum/max/min/cumsum/mean` | sparse |
| `exp(S)`, `cos(S)`, `full(S)` | full |
| `sparse(i,j,v)` duplicates | add (logical entries OR) |
| `sparse(int8(1))` | "Undefined function 'sparse' for input arguments of type 'int8'." |
| display | `(i,j)    v` in column-major order; `All zero sparse: RxC` |

## Adversarial review (done before PR)
| Probe | Finding |
|-------|---------|
| `S(1,2) = 5` on `sparse(2,2)` | stays sparse ✓ |
| `S == 0` | sparse logical; display lists the true entries ✓ |
| `sparse([0 1+2i])` | complex triplet display ✓ |
| `sparse([1 0 1e6])` | values right-aligned, integer format ✓ |
| `sparse(ones(2,2,2))` | N-D error (MATLAB has no N-D sparse) ✓ |
| `S\b` | `\` is not implemented for any matrix yet; noted in #488 |
| `for c = S` | columns are full (MATLAB keeps sparse); noted in #488 |

## Non-goals → residual issue #488
Compressed storage, `spdiags`/`sprand`/`spfun`/`spalloc`, sparse solvers and
`\`, sparse loop variables.
