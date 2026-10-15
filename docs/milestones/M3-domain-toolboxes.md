# M3 — Domain toolboxes

GitHub milestone: https://github.com/superche/openmatlab/milestone/3

**Related:**
- [M-domain-conformance](M-domain-conformance.md): the reference-vector gate for plugins.
- [`../design/PLUGIN-CONTRACT.md`](../design/PLUGIN-CONTRACT.md).
- [`../GAP-ANALYSIS.md`](../GAP-ANALYSIS.md) (M3 rows).
- [M8 Object system](M8-object-system.md) runs interleaved.

## Intent

Domain numerics beyond the core language, written clean-room from public MATLAB/Octave documentation. Several GAP p1 functions already shipped in M7 (Epics #533/#534):
- polyfit/polyval/roots/conv/deconv;
- interp1, trapz/cumtrapz/integral, fzero/fminsearch;
- filter, histcounts/cov/corrcoef;
- readmatrix/writematrix.

This milestone covers what remains.

**Core vs plugin rule:**
- Functions in **base MATLAB** ship in **core**: FFT, interpolation, ODE, basic statistics, JSON, sparse.
- Functions that are a **MathWorks toolbox** in MATLAB ship as **community plugins**, under the locked plugin contract and the domain-conformance gate. Today that is `community.signal`.
- Core never imports a plugin.

Exit criteria and ordering were approved on 2026-10-13.

## Exit criteria (measurable)

M3 is **done** only when **all** of these hold on `main`:

1. **Conformance.** Every criterion in [`tests/conformance/m3_manifest.py`](../../tests/conformance/m3_manifest.py) is `met`, and `pytest tests/conformance/test_m3_conformance.py` reports **0 xfail**. Expected values come from published definitions and reference values.
2. **Plugin gate.** The plugin functions (T06) pass the existing domain gate: reference vectors, plus `which` resolving to the plugin.
3. **No core-to-plugin dependency.**
4. **No open `p0` issue** on milestone/3; CI on `main` green; no doc drift; feature_map rows written; one accepted acceptance package per epic.

## Criteria

| # | Criterion | Script | Priority | Ships as | Epic | Status |
|---|-----------|--------|----------|----------|------|--------|
| T01 | FFT family: `fft`/`ifft` with n and dim, `fft2`/`ifft2`, `fftshift`/`ifftshift`, `nextpow2` | m3_t01_fft | p1 | core | #625 | met (Epic #625; residual #630) |
| T02 | `spline` (not-a-knot and clamped), `pchip`, `ppval`, `interp1` spline/pchip/extrap, `interp2`, `polyder`/`polyint` forms | m3_t02_poly_interp | p1 | core | #626 | met (Epic #626; residual #649) |
| T03 | `ode45`/`ode23` (tspan, odeset, systems), `integral2`, `quad`, `integral` options, `fminbnd`, `optimset` with `fzero`/`fminsearch` | m3_t03_calculus_ode_opt | p1 | core | #627 (#581) | met (Epic #627; residual #657) |
| T04 | `quantile`/`prctile`, `movmean`/`movsum`/`movmedian`, `cummax`/`cummin`, `mode`, `var`/`std` weights, `histc`, `bounds` | m3_t04_stats | p1 | core | #628 (#581) | met (Epic #628; residual #661) |
| T05 | `jsonencode`/`jsondecode`, `csvread` offsets, `dlmwrite` delimiter/precision/append, `dlmread` | m3_t05_data_io | p1 | core | #629 | met (Epic #629; residual #665) |
| T06 | `hann`, `kaiser`, `butter`, `freqz`, `filtfilt`, resolved from `community.signal` | m3_t06_signal_plugin | p2 | plugin | #630 | met (Epic #630; residual #681) |
| T07 | Sparse results stay sparse (comparisons, `~`, arithmetic, indexing, `sum`, `kron`); sparse solves at n=2000 | m3_t07_sparse | p2 | core | #631 (#527) | pending |

## Epics (approved order: E1–E5 interleaved with M8 O-E3/O-E4, then E6–E7)

| Epic | Issue | Priority | Ships as |
|---|---|---|---|
| E1 FFT | #625 | p1 | core |
| E2 Polynomials and interpolation | #626 | p1 | core |
| E3 Calculus, ODE and optimisation | #627 | p1 | core |
| E4 Statistics | #628 | p1 | core |
| E5 Data I/O | #629 | p1 | core |
| E6 `community.signal` breadth | #630 | p2 | plugin |
| E7 Sparse maturity | #631 | p2 | core |

## Progress snapshot

M3 criteria were set on 2026-10-13.

**6 / 7** criteria met: T01 (Epic #625), T02 (Epic #626), T03 (Epic #627), T04 (Epic #628), T05 (Epic #629), T06 (Epic #630). Next: M3-E7 sparse maturity (#631).
