Feature: FD001 degradation metrics (Epic #996)
  The train label is RUL = max(cycle) - cycle within each unit.
  Early and late means use the first and last W cycles. groupsummary
  supplies the per-unit max and the window means.

  @needs_numpy
  Scenario: interleaved units keep row-aligned RUL and sorted window means
    When I evaluate "u = [2;2;2;2;1;1;1;1]; c = [1;2;3;4;1;2;3;4]; s1 = [1;1;3;5;0;0;10;10]; s2 = [0;2;4;8;1;3;5;7]; T = table(u, c, s1, s2, 'VariableNames', {'unit','cycle','s1','s2'}); F = cmapss_failure_cycles(T); fc = F.failure_cycle'; rul = cmapss_train_rul(T)'; [units, early_m, late_m, delta] = cmapss_early_late(T, {'s1','s2'}, 2); er = early_m(1, :); lr = late_m(1, :); d1 = delta(1, :);"
    Then variable "fc" equals row [4, 4]
    And variable "rul" equals row [3, 2, 1, 0, 3, 2, 1, 0]
    And variable "er" equals row [0, 2]
    And variable "lr" equals row [10, 6]
    And variable "d1" equals row [10, 4]
