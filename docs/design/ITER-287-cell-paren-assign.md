# Design: cell paren assign / multi-index delete (Issue #287)

**Epic:** #286 · Absorbs #247

## Decision
1. `c(i)=[]` / `c(i,j)=[]`: empty numeric RHS → delete that cell; rebuild as row if was 1×n else column (same as linear delete).
2. `c(i)={v}` / `c(i,j)={v}`: RHS must be 1×1 CellValue; store `rhs.get(0,0)` at the subscript.
3. Non-cell non-empty RHS → EvalError (MATLAB: conversion to cell from ...).

## Non-goals
Multi-element paren assign `c(1:2)=…` (#110); CSL (#80).
