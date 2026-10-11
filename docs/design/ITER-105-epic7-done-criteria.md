# Feature `done` criteria — Epic #7 (#102) / Issue #105

## lang.cell_assign → done
- Observable: c{i}=v, c{i,j}=v; OOB error; RHS any Value
- Tests: tests/unit/test_cell_assign.py
- Non-goals: grow-on-OOB, A(i)=v

## lang.cell_paren_index → done
- Observable: c(i)/c(i,j) → 1×1 CellValue; array () unchanged
- Tests: tests/unit/test_cell_paren_index.py
- Non-goals: multi-element slices, c(i)=[]
