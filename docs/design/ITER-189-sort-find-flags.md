# Design: sort descend + find first/last (Issue #189)

**Epic:** #188 · Absorbs #95 #96 · Milestone M2 criterion C05

- `sort(A[,dim][,'ascend'|'descend'])` — char flag anywhere after A; stable;
  descend puts NaN first (MATLAB), ascend NaN last. `[B,I]` 1-based.
- `find(X,k[,'first'|'last'])` — at most k linear indices, column-major; `last`
  takes the last k, still ascending.
- Row-vector non-empty input → row-vector output (MATLAB). Empty-row orientation
  and NaN-as-nonzero divergence are tracked as residuals (existing tests not changed).
