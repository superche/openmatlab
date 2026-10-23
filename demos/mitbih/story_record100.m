% MIT-BIH Arrhythmia record 100 (M15 V01, V02, V03).
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

% V03: zero-phase bandpass on MLII, about 0.5-40 Hz. filtfilt is the call.
% bandpass is the same Butterworth order-2 design, so the two traces agree.
x = R.sig(:, 1);
f1 = 0.5;
f2 = 40;
order = 2;
[b, a] = butter(order, [f1 f2] ./ (fs / 2), 'bandpass');
y = filtfilt(b, a, x);
y2 = bandpass(x, [f1 f2], fs);
agree = max(abs(y - y2));
nshow = 10 * fs;
t = (0:nshow-1).' / fs;
xshow = x(1:nshow);
yshow = y(1:nshow);
figure;
plot(t, xshow, t, yshow);
nlines = numel(get(gca, 'Children'));
xlabel('s');
ylabel('mV');
title('MIT-BIH 100 MLII raw and 0.5-40 Hz');
mf = mean(y);
sr = std(x);
sf = std(y);
fprintf('V03 band=0.5-40 order=%.0f nlines=%.0f mean=%.6f std_raw=%.6f std_filt=%.6f agree=%.3e\n', order, nlines, mf, sr, sf, agree);
