# Design — Epic #440 N-D arrays

## First principles
MATLAB dims map 1:1 onto NumPy axes (dim k ↔ axis k-1); all linear views use
column-major (`order="F"`). One invariant keeps shapes MATLAB-true:
`NDArrayValue` drops trailing singleton dims beyond the 2nd at construction.

## Core rule: k-subscript view
For `A(s1,…,sk)` on an array of shape `(d1,…,dn)`:
- `k < n`: fold `dk…dn` into one dim (`A(i,j)` on 2x2x2 addresses columns 1..4);
- `k > n`: pad with 1s.

`index`, `set_index` and `end` (`_eval_subscripts`) all use this one view
(`NumPyArrayBackend._collapsed_shape`), so `end`, reads, writes and grows agree.

## Assignment
- Grow zero-fills to `max(view, subs)` per dim. Growing a folded view, or a
  linear grow on N-D, raises MATLAB's "Attempt to grow array along ambiguous dimension."
- Size check: non-singleton LHS dims must equal non-singleton RHS dims; the
  message is MATLAB's `R-by-C-by-P` form.
- `[]` RHS: exactly one non-colon subscript deletes along that axis (`A(:,:,k)=[]`).

## Builtins
`_shapeN` (zeros/ones/nan/Inf/true/false); `ndims`, `reshape` (one `[]` inferred),
`squeeze`, `cat(dim,…)`. Reductions already took `axis`/`keepdims`, so dim ≥ 3 works.
`*` and `'` on N-D raise MATLAB's errors.

## Display
`A(:,:,k) =` pages in column-major page order; inside cells `[2x2x2 double]`.

## Adversarial review (done before PR)
| Probe | Result |
|-------|--------|
| `A(1,end)` on 2x2x2 | 7 (end = 4 via folding) ✓ |
| `A(1,5)=1` on 2x2x2 | ambiguous-grow error ✓ |
| `A(9)=1` on 2x2x2 | ambiguous-grow error (was silent reshape) — fixed |
| `A(:,3)=[]` on 2x2x2 | 2x3 ✓ |
| `A(:,:,2)=[1 2 3]` | MATLAB size message ✓ |
| `2*A` on N-D | scalar scaling ✓ (early draft wrongly raised) — fixed |
| `zeros(2,3,1)` | size `[2 3]` ✓ |
| 2-D logical `t(1,2)` | class logical (2-sub index used to cast to double) ✓ |
| delete with OOB subscript | "Matrix index is out of range for deletion." (used to grow first) ✓ |

## Non-goals → residual issues
permute/ipermute, N-D in `[ ]` concatenation (`[A B]` with 3-D parts), N-D cells,
flip/circshift/sort along dim ≥ 3 test coverage, MATLAB "Index in position k exceeds array bounds" wording.
