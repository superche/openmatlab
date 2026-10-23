function R = load_record100()
%LOAD_RECORD100  MIT-BIH Arrhythmia Database record 100, in millivolts.
%   R = load_record100() downloads 100.hea, 100.dat and 100.atr into
%   downloads/mitbih/ when they are not already cached, then reads the record.
%
%   R.fs is 360. R.sig is samples-by-channels, in mV
%   (adc - baseline) / gain. R.names holds the header descriptions (MLII, V5).
%   R.ann_sample is the optional annotation index (1-based). It is not a
%   diagnostic golden.
%
%   The three PhysioNet files are never committed.
%
%   Licence: ODC-By 1.0. Data DOI: 10.13026/C2F305.
%   G. B. Moody and R. G. Mark, IEEE Eng. Med. Biol. Mag. 20(3):45-50, 2001.
%   A. L. Goldberger et al., Circulation 101(23):e215-e220, 2000.

root = mitbih_fetch();
R = mitbih_load(root);
end
