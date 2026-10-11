# ITER-002 Design: Concrete Array + NumPyArrayBackend

**Issue:** #2  
**Principles:** AGENTS.md — KISS, LSP, high cohesion / low coupling

## Goal

Give the runtime a real **array-first** value type and a NumPy-backed
`ArrayBackend`, without wiring the language evaluator yet.

## Design

| Piece | Choice | Why |
|-------|--------|-----|
| `NDArrayValue` | Thin wrapper over `numpy.ndarray` in `numerics/ndarray_value.py` | Keeps `runtime.value` Protocol-only (no hard NumPy import in runtime core) |
| Scalar | `numel() == 1` ⇒ `is_scalar()`; `from_scalar` → shape `(1, 1)` | Public MATLAB-like scalar-as-1×1 |
| `NumPyArrayBackend` | Implements `ArrayBackend`; lazy-imports numpy | Optional `[numpy]` extra; CI installs it |
| Errors | `NumericsError` for shape/op failures | Clear seam; not bare `ValueError` soup |

## Non-goals (this iteration)

- Lexer/parser/evaluator
- Complex dtype / sparse
- Plotting

## Test plan

- Unit: shape, scalar 1×1, zeros/ones/eye, from_nested, matmul, elem_mul, add
- Gherkin: array scalar + matmul smoke
- Marker `needs_numpy`; CI installs `.[dev,numpy]`

## Adversarial notes

- Do **not** put ndarray into `runtime.value` Protocol module (coupling).
- Do **not** weaken tests if NumPy missing — skip only via marker when extra absent; CI must have NumPy.
