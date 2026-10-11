# Feature `done` criteria — Epic #6 (#87) / Issue #91

## libs.cumsum → done
- Observable: cumsum(A), cumsum(A,dim); first non-singleton default
- Tests: tests/unit/test_cumsum.py
- Non-goals: N-D >2

## libs.sort → done
- Observable: ascending sort; optional dim; [B,I]=sort 1-based stable
- Tests: tests/unit/test_sort.py
- Non-goals: 'descend', ComparisonMethod

## libs.find → done
- Observable: find(X), find(X,k); [r,c], [r,c,v]; column-major; skip NaN
- Tests: tests/unit/test_find.py
- Non-goals: 'first'/'last' string flags
