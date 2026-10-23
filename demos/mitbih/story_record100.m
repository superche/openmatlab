% MIT-BIH Arrhythmia record 100 (M15 V01, V02).
% Licence: ODC-By 1.0. Data DOI: 10.13026/C2F305.
% Moody and Mark, IEEE Eng. Med. Biol. Mag. 20(3):45-50, 2001.
% Goldberger et al., Circulation 101(23):e215-e220, 2000.
% 100.hea, 100.dat and 100.atr stay in downloads/mitbih/ and are never committed.
%
% From the repository root:
%   openmatlab -e "run('demos/mitbih/story_record100.m')"

here = fileparts(mfilename('fullpath'));
addpath(here);
R = load_record100();
fs = R.fs;
nch = size(R.sig, 2);
ns = size(R.sig, 1);
s0 = R.sig(1, 1);
fprintf('MIT-BIH record 100 Fs=%.0f channels=%.0f samples=%.0f MLII_mV0=%.6f\n', fs, nch, ns, s0);
