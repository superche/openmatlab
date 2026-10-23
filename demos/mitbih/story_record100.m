% MIT-BIH Arrhythmia record 100 (M15 V01-V06).
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
mf = mean(y);
sr = std(x);
sf = std(y);

% V04: R peaks on the filtered MLII. Height 0.5 mV, at least 0.25 s apart.
% .atr is not the detector and is not a golden.
height = 0.5;
mindist = round(0.25 * fs);
[pks, locs] = findpeaks(y, 'MinPeakHeight', height, 'MinPeakDistance', mindist);
npeaks = numel(locs);
rr = diff(locs) ./ fs;
mean_rr = mean(rr);
win = find(locs <= nshow);
npeaks_win = numel(win);

% V05: one-sided amplitude spectrum of the 10 s filtered excerpt.
spec = abs(fft(yshow));
spec(1) = 0;
nh = floor(nshow / 2) + 1;
[fft_mag, fft_bin] = max(spec(1:nh));
fpeak = (fft_bin - 1) * fs / nshow;
freqs = (0:nh-1).' * fs / nshow;

% Peak, RR, and spectrum panels first. The V03 axes stay the last figure.
figure;
plot(t, yshow);
hold on;
plot(t(locs(win)), pks(win), 'o');
npeak_lines = numel(get(gca, 'Children'));
xlabel('s');
ylabel('mV');
title('MIT-BIH 100 MLII R peaks');

figure;
histogram(rr * 1000);
xlabel('RR (ms)');
ylabel('count');
title('MIT-BIH 100 RR histogram');

figure;
plot(freqs, spec(1:nh));
xlim([0 60]);
xlabel('Hz');
ylabel('mV');
title('MIT-BIH 100 MLII amplitude spectrum');

% V06: one 2x2 lab figure. The V03 axes are created after it so they stay last.
fig_lab = figure;
tl = tiledlayout(2, 2, 'TileSpacing', 'compact', 'Padding', 'loose');
tl.Title.String = 'MIT-BIH record 100';
tl.XLabel.String = sprintf('G. B. Moody and R. G. Mark, IEEE Eng. Med. Biol. Mag. 20(3):45-50, 2001.\nA. L. Goldberger et al., Circulation 101(23):e215-e220, 2000.\nData: DOI 10.13026/C2F305 (ODC-By 1.0).');
nexttile;
plot(t, xshow);
xlabel('s');
ylabel('mV');
title('record 100 MLII raw');
nexttile;
plot(t, yshow);
hold on;
plot(t(locs(win)), pks(win), 'o');
xlabel('s');
ylabel('mV');
title('record 100 MLII filtered, R peaks');
nexttile;
histogram(rr);
xlabel('s');
ylabel('count');
title('record 100 RR');
nexttile;
plot(freqs, spec(1:nh));
xlim([0 60]);
xlabel('Hz');
ylabel('mV');
title('record 100 MLII spectrum');
gs = tl.GridSize;
ntiles = numel(tl.Children);

figure;
plot(t, xshow, t, yshow);
nlines = numel(get(gca, 'Children'));
xlabel('s');
ylabel('mV');
title('MIT-BIH 100 MLII raw and 0.5-40 Hz');

fprintf('V03 band=0.5-40 order=%.0f nlines=%.0f mean=%.6f std_raw=%.6f std_filt=%.6f agree=%.3e\n', order, nlines, mf, sr, sf, agree);
fprintf('V04 peaks=%.0f mean_rr=%.6f rr_n=%.0f peaks_10s=%.0f height=%.3f mindist=%.0f npeak_lines=%.0f\n', npeaks, mean_rr, numel(rr), npeaks_win, height, mindist, npeak_lines);
fprintf('V05 fpeak=%.6f fft_mag=%.6f nh=%.0f\n', fpeak, fft_mag, nh);
fprintf('V06 grid=%.0f %.0f tiles=%.0f\n', gs(1), gs(2), ntiles);
