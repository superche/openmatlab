# EPIC-630: community.signal plugin breadth (M3-E6)

Criterion **T06** (`m3_t06_signal_plugin`) in [M3](../milestones/M3-domain-toolboxes.md). Ships as the **community.signal** plugin under the [plugin contract](PLUGIN-CONTRACT.md); core does not import it.

## Functions (demos/plugins/community.signal/mfiles/)
| Function | Notes |
|---|---|
| `hann(n[, 'symmetric'\|'periodic'])` | Column window. Formula from public MATLAB/Octave docs. |
| `kaiser(n[, beta])` | Shape parameter (default 0.5). `I0` by its power series, so no special-function builtin is required. |
| `butter(n, Wn[, 'low'\|'high'])` | Analog Butterworth poles, `Omega = tan(pi*Wn/2)` prewarp, bilinear `z = (1+s)/(1-s)`, zeros at ±1, DC/Nyquist gain 1. |
| `freqz(b, a[, n\|w][, 'whole'])` | Horner's method on `e^{-jw}`; default n = 512 on `[0, π)`. |
| `filtfilt(b, a, x)` | Odd reflection of `3*(nfilt-1)` samples and Gustafsson initial conditions, then forward and reverse `filter`. Vectors keep their orientation. |

Existing windows (`hamming`, `rectwin`, `blackman`) are unchanged. The plugin still activates through `plugin.yaml` `pathEntries: mfiles`.

## Adversarial review
| Probe | Result |
|---|---|
| Conformance T06 expected JSON | Matches for all 13 checks. |
| `which('hann')` with the plugin on the path | Path contains `community.signal`. |
| `butter(1, 0.5)` | `[0.5 0.5]`, `[1 0]`. |
| `kaiser(7, 0)` | All ones; sum is 7. |
| Empty-range pad `b(end+1:nf)=0` | Avoided in filtfilt (`b(nf)=0` when needed). Core still errors on empty linear assign (residual). |
| Existing domain D01–D04 | Still pass. |

No existing test or conformance expected file changed.

## Residuals
https://github.com/superche/openmatlab/issues/681
