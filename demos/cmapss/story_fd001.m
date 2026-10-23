% NASA C-MAPSS FD001 story (M14 V01, V02, V03).
% Saxena, Goebel, Simon, and Eklund, PHM08.
% Data: DOI 10.5281/zenodo.15346912 (CC BY 4.0).
% The zip and the text files stay in downloads/cmapss/ and are never committed.
%
% From the repository root:
%   openmatlab -e "run('demos/cmapss/story_fd001.m')"

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
