# Feature `done` criteria — Epic #8 (#115) / Issue #117

## lang.array_assign → done
- Observable: A(i,j)=v, A(k)=v scalar RHS; OOB error; read-after-write
- Tests: tests/unit/test_array_assign.py
- Non-goals: grow, A(i)=[], range/logical LHS, non-scalar RHS

## numerics.array_set → done
- Observable: ArrayBackend.set_index COW 1-based
- Tests: tests/unit/test_array_assign.py
