% NASA C-MAPSS FD001 story (M14 V01, V02, V03, V04).
% Saxena, Goebel, Simon, and Eklund, PHM08.
% Data: DOI 10.5281/zenodo.15346912 (CC BY 4.0).
% The zip and the text files stay in downloads/cmapss/ and are never committed.
%
% From the repository root:
%   openmatlab -e "run('demos/cmapss/story_fd001.m')"
%
% V04 metrics (public formulas, not a PHM08 model):
%   failure cycle = max(cycle) per unit          (groupsummary)
%   train RUL     = failure cycle - cycle        (0 on the last cycle)
%   early / late  = mean of the first / last 30 cycles of each kept sensor
%   correlation   = Pearson sample correlation of the kept sensors

here = fileparts(mfilename('fullpath'));
addpath(here);
T = load_fd001('train');
h = height(T);
w = width(T);
u = numel(unique(T.unit));
n1 = sum(T.unit == 1);
fprintf('FD001 train height=%g width=%g unique_units=%g unit1_cycles=%g\n', h, w, u, n1);

% V03. One unit. Drop sensors whose sample std is at most 1e-6 (FD001 idle
% channels sit on numerical dust). Smooth the busiest remaining channel and
% draw raw plus both smoothers on the same axes. Window 15 is the call a script would write.
unit_id = 1;
win = 15;
U = T(T.unit == unit_id, :);
sens = cmapss_names();
sens = sens(6:26);
S = table2array(U(:, 6:end));
sig = std(S, 0, 1);
keep = sig > 1e-6;
ndrop = sum(~keep);
nkeep = sum(keep);
dropped = sens(~keep);
kept_names = sens(keep);
[~, ix] = max(sig(keep));
picked = kept_names{ix};
Sk = S(:, keep);
raw = Sk(:, ix);
sm = smoothdata(raw, 'movmean', win);
sg = smoothdata(raw, 'gaussian', win);
chk = movmean(raw, win);
agree = max(abs(sm - chk));
sg_ok = all(isfinite(sm)) && all(isfinite(sg));
changed = max(abs(sm - raw)) > 0 && max(abs(sg - raw)) > 0;
drop_sig = sig(~keep);
if isempty(drop_sig)
    drop_max = 0;
else
    drop_max = max(drop_sig);
end
keep_min = min(sig(keep));
cyc = U.cycle;

% V04. Same 1e-6 idle-channel rule, applied to every training row. A channel
% that is dust on unit 1 can still move across the fleet (sensor_6 does).
% Window 30 is the first and last 30 cycles (the shortest FD001 life is
% longer than 60, so the windows do not overlap). Each unit is weighted once.
W = 30;
A = table2array(T(:, 6:end));
fleet_sig = std(A, 0, 1);
fleet_keep = fleet_sig > 1e-6;
metric_names = sens(fleet_keep);
same_drop = all(fleet_keep(:) == keep(:));
F = cmapss_failure_cycles(T);
fc = F.failure_cycle;
rul = cmapss_train_rul(T);
rul_u1 = rul(T.unit == unit_id);
n_rul0 = sum(rul == 0);
[units, early_m, late_m, delta] = cmapss_early_late(T, metric_names, W);
fleet_early = mean(early_m, 1);
fleet_late = mean(late_m, 1);
fleet_delta = mean(delta, 1);
C = cmapss_sensor_corr(A(:, fleet_keep));
p = size(C, 1);
corr_offmax = -inf;
corr_i = 1;
corr_j = 1;
for j = 1:p
    for i = 1:p
        if i ~= j && C(i, j) > corr_offmax
            corr_offmax = C(i, j);
            corr_i = i;
            corr_j = j;
        end
    end
end
early_y = raw(cyc <= W);
late_y = raw(cyc > max(cyc) - W);
spec = abs(fft(raw));
spec(1) = 0;
nh = floor(numel(raw) / 2) + 1;
[fft_mag, fft_bin] = max(spec(1:nh));

% Panels (b)(c)(d) first, so the V03 figure stays the last one.
figure;
tiledlayout(2, 2);
nexttile;
tw = (1:numel(early_y))';
plot(tw, early_y, tw, late_y);
xlabel('window index');
ylabel(picked);
title('FD001 unit 1 early vs late');
legend('early', 'late');
nexttile;
imagesc(C, [-1 1]);
colorbar;
axis image;
title('FD001 sensor correlation');
xticks(1:p);
xticklabels(metric_names);
yticks(1:p);
yticklabels(metric_names);
nexttile;
histogram(fc);
xlabel('failure cycle');
ylabel('units');
title('FD001 train failure cycles');
nexttile;
plot(cyc, rul_u1);
xlabel('cycle');
ylabel('RUL');
title('FD001 unit 1 train RUL');

figure;
plot(cyc, raw, cyc, sm, cyc, sg);
xlabel('cycle');
ylabel(picked);
title('FD001 unit 1: raw and smoothdata');
legend('raw', 'movmean', 'gaussian');
nlines = numel(get(gca, 'Children'));

fprintf('V03 dropped');
for k = 1:numel(dropped)
    fprintf(' %s', dropped{k});
end
fprintf('\n');
fprintf('V03 unit=%g dropped=%g kept=%g picked=%s window=%g movmean_agree=%g nlines=%g drop_max=%g keep_min=%g\n', unit_id, ndrop, nkeep, picked, win, agree, nlines, drop_max, keep_min);
fprintf('V04 window=%g sensors=%g same_drop=%g\n', W, numel(metric_names), same_drop);
fprintf('V04 sensor early late delta\n');
for k = 1:numel(metric_names)
    fprintf('V04 %s %g %g %g\n', metric_names{k}, fleet_early(k), fleet_late(k), fleet_delta(k));
end
fprintf('V04 fail_min=%g fail_median=%g fail_max=%g n_units=%g rul0=%g rul_max=%g\n', min(fc), median(fc), max(fc), numel(fc), n_rul0, max(rul));
fprintf('V04 corr_offmax=%g %s %s\n', corr_offmax, metric_names{corr_i}, metric_names{corr_j});
fprintf('V04 fft_bin=%g fft_mag=%g\n', fft_bin, fft_mag);
