function [units, early_m, late_m, delta] = cmapss_early_late(T, sensors, W)
%CMAPSS_EARLY_LATE  Per-unit sensor means on the first and last W cycles.
%   [units, early_m, late_m, delta] = cmapss_early_late(T, sensors, W)
%
%   failure_cycle(u) = max cycle of unit u (cmapss_failure_cycles).
%   Early rows are cycle <= W. Late rows are cycle > failure_cycle - W.
%   Each window must contain exactly W rows, and failure_cycle >= 2*W so
%   the windows do not overlap. On FD001, cycles are 1..N with no gaps, so
%   this is the first W cycles and the last W cycles.
%
%   early_m(u, s) and late_m(u, s) are groupsummary means (NaNs omitted).
%   FD001 has no missing values, so that is the arithmetic mean. delta is
%   late_m - early_m. units is ascending, one row per unit. sensors is a
%   cellstr or a name; columns of the three matrices follow that order.
%
%   A fleet number is the unweighted mean across units (each unit counts
%   once). With exactly W rows in every window, that equals the pooled mean.

if nargin < 3
    W = 30;
end
if numel(W) ~= 1 || ~(W >= 1) || W ~= floor(W)
    error('OpenMATLAB:cmapss:Window', 'cmapss_early_late: W must be a positive integer.');
end
F = cmapss_failure_cycles(T);
if any(F.failure_cycle < 2 * W)
    error('OpenMATLAB:cmapss:Window', ...
        'cmapss_early_late: a unit is shorter than 2*W, so the early and late windows overlap.');
end
J = join(T, F, 'Keys', 'unit');
E = groupsummary(J(J.cycle <= W, :), 'unit', 'mean', sensors);
L = groupsummary(J(J.cycle > J.failure_cycle - W, :), 'unit', 'mean', sensors);
if height(E) ~= height(F) || height(L) ~= height(F) || any(E.unit ~= F.unit) || any(L.unit ~= F.unit)
    error('OpenMATLAB:cmapss:Window', 'cmapss_early_late: a unit has an empty early or late window.');
end
if any(E.GroupCount ~= W) || any(L.GroupCount ~= W)
    error('OpenMATLAB:cmapss:Window', ...
        'cmapss_early_late: a window does not have exactly W cycles (gap or duplicate cycle).');
end
units = E.unit;
early_m = table2array(E(:, 3:end));
late_m = table2array(L(:, 3:end));
delta = late_m - early_m;
end
