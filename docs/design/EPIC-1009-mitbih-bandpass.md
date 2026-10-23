# Epic #1009 (B-E2): zero-phase 0.5–40 Hz bandpass

Milestone: [M15 MIT-BIH Arrhythmia vertical](../milestones/M15-mitbih-vertical.md), criterion V03.

## Problem

After record 100 is in millivolts, the scientist bandpass-filters one channel at about 0.5–40 Hz with no phase shift, and looks at raw and filtered on the same axes. `community.signal` already has `filtfilt` and a low/high `butter`. It has no bandpass, and a core name shadows an m-file on the path, so the ECG call has to live where `filtfilt` actually resolves.

## Design

- **`filtfilt(b, a, x)`** in `libs/filtfilt.py`. Normalize `a(1)`, pad to a common length, reflect `3*(nfilt-1)` samples oddly at each end, and run direct-form II transposed forward then backward from Gustafsson's steady-state initial condition. Row vectors stay rows. Matrices go down the columns. The recurrence is the same one `filter` uses.
- **`butter(n, Wn)` and `butter(n, Wn, 'high')`** keep the existing lowpass and highpass formulas (analog poles, `tan(pi*Wn/2)` prewarp, bilinear map, gain at DC or Nyquist). A two-element `Wn` is bandpass of order `2n`: each prototype pole becomes a quadratic, `n` zeros sit at `z = +1` and `n` at `z = -1`, and the gain is 1 at the prewarped geometric center. `'bandpass'` is explicit or the default when `Wn` has two edges.
- **`bandpass(x, [f1 f2], fs)`** optional 4th-argument order, default 2. It designs that Butterworth and calls `filtfilt`. Frequencies are Hz. This is not MATLAB's minimum-order `bandpass` and not a `designfilt` object.
- **Story.** `demos/mitbih/story_record100.m` keeps the V01/V02 print. It then takes MLII, calls `butter(2, [0.5 40]/(fs/2), 'bandpass')` and `filtfilt`, checks `bandpass` on the same column, and plots the first 10 s of both traces on one axes.

The 0.5 Hz and 40 Hz edges are the half-power points of one `butter` pass. `filtfilt` squares the magnitude, so a tone in the middle of the band (10 Hz at 360 Hz) stays near unit amplitude and a constant is removed.

## Non-goals

`designfilt`, dsp System objects, GPU, bandstop, and an SOS form. R-peak detection is B-E3 ([#1010](https://github.com/superche/openmatlab/issues/1010)).

## Adversarial review

| Attack | Result |
|---|---|
| Core `filtfilt` / `butter` shadow `community.signal` | Lowpass `butter(2, 0.5)` and `butter(1, 0.5)`, the ramp `filtfilt([0.5 0.5], 1, 1:10)`, and the constant row of 5s still match the existing goldens. `which('hann')` still resolves to the plugin |
| Short input (`length <= 3*(nfilt-1)`) | `signal:filtfilt:InvalidDimensions` before a sample is emitted |
| `Wn` outside `(0, 1)`, or a band with `f2 >= fs/2` | `signal:butter:invalidCutoff` or `signal:bandpass:invalidFpass` |
| Bandpass gain left at the polynomial scale | The numerator is divided by `H(exp(j*wc))` at the prewarped geometric center. Cutoffs sit at `1/sqrt(2)` |
| Plotting all 650000 samples | The figure is the first 10 s (3600 samples). The filter still sees the whole MLII column |
| `bandpass` drifting from `filtfilt` | Same design function and same `filtfilt`. The story's `agree` is the max absolute difference |
| Existing tests | Not modified |
