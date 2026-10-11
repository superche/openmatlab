# Design: matrix/scalar power ^ (Issue #224)

**Epic:** #223 · Absorbs #193 · M2 C11

## Decision
`ArrayBackend.power(..., elementwise=False)`:

1. Both 1×1 → ordinary float power (`**`).
2. Left m×m, right 1×1 integer → `numpy.linalg.matrix_power` (supports negative int if invertible; we allow any int).
3. Else → NumericsError with clear message.

`.^` path unchanged (`elementwise=True`).

## Non-goals
`2^A` matrix exponential, fractional matrix powers, complex results beyond float64.
