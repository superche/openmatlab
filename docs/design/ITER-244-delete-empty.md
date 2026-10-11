# Design: delete via A(i)=[] / c(i)=[] (Issue #244)

**Epic:** #243 · Absorbs #120 #109 · M2 C06

## Decision
1. `set_index` when RHS `numel==0`: **delete** selected linear indices (1-sub);
   keep row/col orientation for vectors; matrices → column of remaining.
2. Also support 2-sub row/col delete: `A(i,:)=[]` / `A(:,j)=[]` when one side is full colon-all (vector of all indices) — if free; else residual.
3. `ArrayAssign` on `CellValue`: `c(i)=[]` removes that linear cell; rebuild CellValue.

Detect delete by `rhs.numel()==0` (empty `[]`).

## Non-goals
Grow (C08); multi-dim partial block delete beyond row/col.
