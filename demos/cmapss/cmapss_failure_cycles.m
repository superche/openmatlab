function F = cmapss_failure_cycles(T)
%CMAPSS_FAILURE_CYCLES  Per-unit failure cycle on a C-MAPSS train table.
%   F = cmapss_failure_cycles(T) is groupsummary(T, 'unit', 'max', 'cycle')
%   with the columns renamed. F.unit is ascending. F.failure_cycle is the
%   maximum cycle of that unit. F.n_cycles is the number of rows.
%
%   The train label at a row is failure_cycle(unit) - cycle. See
%   cmapss_train_rul. This is the public piecewise definition (RUL is 0 on
%   the last cycle). It is not a PHM08 contest model.

G = groupsummary(T, 'unit', 'max', 'cycle');
F = table(G.unit, G.max_cycle, G.GroupCount, 'VariableNames', {'unit', 'failure_cycle', 'n_cycles'});
end
