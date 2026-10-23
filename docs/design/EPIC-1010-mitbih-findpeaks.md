# Epic #1010 (B-E3): R peaks, RR, and an amplitude spectrum

Milestone: [M15 MIT-BIH Arrhythmia vertical](../milestones/M15-mitbih-vertical.md), criteria V04 and V05.

## Problem

The filtered MLII lead needs R peaks, an RR series with a histogram, and one amplitude spectrum. The call is `findpeaks` with `MinPeakHeight` and `MinPeakDistance`. The peak locations on the demo window have to sit within about 1–2 samples of a fixed rule. `.atr` may be drawn later; it is not the detector.

## Design

- **`findpeaks(y)`** in `libs/findpeaks.py`. A peak is the first sample of a run that is strictly higher than the samples on both sides. `MinPeakHeight` drops anything shorter. `MinPeakDistance` then walks peaks from tallest to shortest and drops a peak that is closer than that distance to one already kept. An equal height keeps the earlier index.
- **Locations.** With no second argument, locations are 1-based sample indices and the distance is in samples. A positive scalar second argument is the sample rate: locations are seconds from 0, and the distance is in seconds. A location vector of the same length is accepted and the distance uses those units.
- **Story thresholds.** Height 0.5 mV and `round(0.25*fs)` samples (90 samples, 0.25 s) on the full filtered MLII column. RR is `diff(locs)/fs` in seconds. The histogram is RR in milliseconds. The spectrum is `abs(fft)` of the first 10 s, DC bin cleared, one-sided, viewed from 0 to 60 Hz.
- **Figures.** The peak markers, the RR histogram, and the spectrum are separate figures with axis labels. The raw-versus-filtered axes stay the last figure, so the V03 check still sees that panel. One `tiledlayout` with the citation footnote is V06 (B-E4).
- **Window check.** Peaks whose index falls in the first 10 s are compared with the same local-maximum rule run on the filtered column. The closed-form golden is a 1.2 Hz sine at 360 Hz: the crest is sample 76 and the period is 300 samples.

## Non-goals

Prominence, width, `NPeaks`, `SortStr`, and `spectrogram`. A Pan-Tompkins implementation. An arrhythmia classifier. The lab-meeting tiled figure (B-E4, [#1011](https://github.com/superche/openmatlab/issues/1011)).

## Adversarial review

| Attack | Result |
|---|---|
| Flat top | The first sample of the run is the peak. `[0 1 1 1 0]` returns index 2 |
| Two peaks inside `MinPeakDistance` | The taller one is kept. Equal height keeps the earlier index |
| Endpoint | Not a peak. A peak needs a sample on both sides |
| Matrix `Y` | `signal:findpeaks:expectedVector` |
| Negative distance | `signal:findpeaks:invalidDistance` |
| Using `.atr` as the golden | Not done. The gate is the sine crest and the local-maximum rule on the demo window |
| V03 figure no longer last | Peak, histogram, and spectrum are drawn first. The bandpass axes are created last |
| Existing tests | Not modified |
