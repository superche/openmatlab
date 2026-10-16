# Epic #766 C-E6: corpus burn-down (rolling)

## Scope
Burn down M12 corpus failures toward C05 (T0 ≥ 95 %), C06 (T1 ≥ 65 %) and C09 (internal-crash = 0). Thresholds are locked; this epic does not change them.

## Increment 1: C09 internal crashes (PR #839)
- Design: the two `internal-crash` groups in the first full run were (a) `*` width/precision in `sprintf`/`fprintf` raising a Python error, and (b) `display` called for unsuppressed statements inside function bodies. Fix both in the builtin layer so the user gets MATLAB output or a MATLAB-style error, never a traceback.
- Adversarial review: `*` with negative, non-integer and missing arguments; `*` combined with precision; display inside nested and anonymous functions. Residual: function-body display output still differs from MATLAB (#838).
- Evidence: full corpus re-run reports `internal-crash` = 0 (REPORT.md, T0 87.5 %, T1 26.2 %).

## Next increments
Ranked by T1 impact from the corpus issues #793-#831, interleaved with C-E5 #765 and M13 epics.
