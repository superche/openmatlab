# MIT-BIH record 100

Runtime download of PhysioNet record 100 only. The `.hea`, `.dat` and `.atr` files are cached under `downloads/mitbih/` and are not part of this repository.

```bash
openmatlab -e "run('demos/mitbih/story_record100.m')"
```

The story prints Fs, the channel count, the sample count, and the first MLII sample in mV. It then zero-phase bandpass-filters MLII at 0.5–40 Hz (`filtfilt`, with `bandpass` as the same order-2 Butterworth) and plots the first 10 s of raw and filtered on one axes. On the filtered column it marks R peaks (`findpeaks`, 0.5 mV, 0.25 s apart), draws an RR histogram, and plots the amplitude spectrum of that 10 s excerpt.

Licence: ODC-By 1.0. Data DOI: [10.13026/C2F305](https://doi.org/10.13026/C2F305).

- G. B. Moody and R. G. Mark, The impact of the MIT-BIH Arrhythmia Database, IEEE Engineering in Medicine and Biology Magazine, 20(3):45–50, 2001.
- A. L. Goldberger et al., PhysioBank, PhysioToolkit, and PhysioNet, Circulation 101(23):e215–e220, 2000.
