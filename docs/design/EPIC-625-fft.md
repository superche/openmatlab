# EPIC-625: FFT family (M3-E1)

Criterion **T01** (`m3_t01_fft`) in [M3](../milestones/M3-domain-toolboxes.md).

## Scope
`fft`, `ifft`, `fft2`, `ifft2`, `fftn`, `ifftn`, `fftshift`, `ifftshift`, `nextpow2`, shipped in core as `openmatlab/libs/fft.py` and registered through `numeric_builtins`.

## Semantics
- `fft(X)` operates along the first non-singleton dimension. `fft(X, n)` zero-pads or truncates to `n`, and `n = []` keeps the size. `fft(X, n, dim)` operates along `dim`, adding trailing singleton dimensions as needed.
- `fft` always returns a complex result, as MATLAB does. `ifft(..., 'symmetric')` returns the real part, and `'nonsymmetric'` is accepted.
- `fft([])` returns an empty result. If `n` is not a nonnegative integer, the call raises `MATLAB:fftfcn:lengthNotNonnegInt`.
- `fft2(X, m, n)` / `fft2(X, [m n])` transform along dims 1–2. `fftn(X, siz)` transforms along `numel(siz)` dims.
- `fftshift(X)` shifts every dimension. `fftshift(X, dim)` shifts only `dim`, and a dim beyond `ndims` leaves X unchanged.
- `nextpow2(n)` is elementwise `ceil(log2(abs(n)))`, with `nextpow2(0) = 0` and `Inf` passed through.

## Backend
numpy.fft (pocketfft). Numerically identical to FFTW up to rounding, so tests compare within tolerance.

## Tests
- `tests/unit/test_fft.py`
- `features/fft.feature`
- conformance `m3_t01_fft`

## Residuals
- `fft` on integer/single classes preserving `single` → tracked with typed numerics.
- `filtfilt` → M3-E6 (#630).
