function rul = cmapss_train_rul(T)
%CMAPSS_TRAIN_RUL  Train RUL = max(cycle) - cycle within each unit.
%   rul = cmapss_train_rul(T) is a column aligned with the rows of T.
%   The last cycle of each unit has RUL 0. join keeps the left-table order,
%   so the result lines up with T even when units are interleaved.
%
%   Public formula, not a learned RUL model. Test-set RUL_FD001 is a
%   different vector (one value per unit at the end of the test trace).

F = cmapss_failure_cycles(T);
J = join(T, F, 'Keys', 'unit');
rul = J.failure_cycle - J.cycle;
end
