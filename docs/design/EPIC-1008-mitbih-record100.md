# Epic #1008 (B-E1): MIT-BIH record 100 download and format 212 load

Milestone: [M15 MIT-BIH Arrhythmia vertical](../milestones/M15-mitbih-vertical.md), criteria V01 and V02.

## Problem

An ECG script starts by downloading PhysioNet MIT-BIH record 100 and reading the two leads in millivolts at 360 Hz. The bytes must not enter the repository. OpenMATLAB has no WFDB reader, so this epic adds a minimal clean-room one for this record only.

## Design

- **Manifest.** `demos/mitbih/manifest.json` is metadata only: the PhysioNet base URL, DOI 10.13026/C2F305, ODC-By 1.0, the three filenames, byte sizes, and sha256. No `.hea`, `.dat`, or `.atr` bytes.
- **Fetch.** `libs/mitbih.py` (`python -m openmatlab.libs.mitbih fetch`, or MATLAB `mitbih_fetch`) writes `downloads/mitbih/100.hea`, `100.dat`, and `100.atr`. Each file is checked against the manifest size and sha256. A match is not downloaded again. `$OPENMATLAB_MITBIH_CACHE` overrides the cache root. The URL path is the manifest name appended to the locked base URL, so a response cannot choose a different filename.
- **Header.** Comment lines (`#`) are skipped. The record line supplies the name, signal count, `Fs`, and sample count. Each signal line supplies format, gain, ADC resolution, baseline, initial value, checksum, block size, and description. A gain written as `200(11)/mV` is accepted. Missing units default to `mV`, which is the MIT-BIH calibration (200 ADC units per mV).
- **Format 212.** The header ADC resolution is 11. The on-disk format code is 212: two 12-bit two's-complement samples packed into three bytes. The 12th bit is the sign. The reader does not mask to 11 bits. Both channels share one file, so the file is read once.
- **Millivolts.** `mV = (adc - baseline) / gain`. The first sample must equal the header initial value, and each channel's 16-bit signed checksum must equal the header checksum.
- **Annotations.** `.atr` is parsed when the file is present (sample delta, SKIP, aux). MATLAB `ann_sample` is 1-based. This overlay is not a diagnostic golden and is not an exit number for V02 beyond "the list is ordered and inside the record".
- **Loader.** `demos/mitbih/load_record100.m` calls `mitbih_fetch` then `mitbih_load`. `demos/mitbih/story_record100.m` prints `Fs`, channel count, sample count, and the first MLII sample in mV.
- **Signal filenames.** A header name that is not a single path segment (`../evil.dat`) is rejected before any read.

Citation recorded in the module, the loader, and the demo: Moody & Mark, IEEE EMB 2001; Goldberger et al., Circulation 2000; DOI 10.13026/C2F305; ODC-By 1.0.

## Non-goals

Any record other than 100. The full MIT-BIH zip. A WFDB toolbox. Copying GPL PhysioNet MATLAB sources. Bandpass, R-peak detection, the lab figure, and export (B-E2…B-E6, epics #1009–#1013).

## Adversarial review

| Attack | Result |
|---|---|
| File of the wrong size or sha256 | `RuntimeError` from `verify_cached`; the bad file is deleted and the download retried |
| Download error | Three attempts, then `mitbih_fetch: could not download …` |
| Header filename `../evil.dat` | Rejected as not a single path segment. Nothing is read outside the record directory |
| Format other than 212, or a non-zero block size | `RuntimeError` before a sample is interpreted |
| Checksum or initial value does not match the decoded ADC | `RuntimeError`. A shifted 212 nibble fails here |
| Masking the 12-bit word to 11 bits | Not done. The negative V5 range needs the sign bit in the 12-bit field |
| `.atr` with a short AUX or an odd length | `RuntimeError` on a truncated aux. A well-formed aux drops its trailing NUL |
| `mitbih_fetch` with an argument | `MATLAB:TooManyInputs` before any download |
| Cache path | `git check-ignore` reports `downloads/`. `downloads/mitbih/` restates the M15 policy. `git ls-files` does not list the three files |
| Existing tests | Not modified |
