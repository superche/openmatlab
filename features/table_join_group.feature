Feature: joins and grouping (Epic #696)
  @needs_numpy
  Scenario: innerjoin keeps matching keys in key order
    Given a fresh session
    When I evaluate "A = table([1;2;3], [10;20;30], 'VariableNames', {'k','x'}); B = table([3;1;4], [300;100;400], 'VariableNames', {'k','y'}); I = innerjoin(A, B); v = I.y';"
    Then variable "v" equals row [100, 300]

  @needs_numpy
  Scenario: outerjoin with merged keys covers both tables
    Given a fresh session
    When I evaluate "A = table([1;2;3], [10;20;30], 'VariableNames', {'k','x'}); B = table([3;1;4], [300;100;400], 'VariableNames', {'k','y'}); O = outerjoin(A, B, 'MergeKeys', true); v = O.k';"
    Then variable "v" equals row [1, 2, 3, 4]

  @needs_numpy
  Scenario: splitapply sums per group
    Given a fresh session
    When I evaluate "v = splitapply(@sum, [10;20;30;40;50], findgroups([1;2;1;2;3]))';"
    Then variable "v" equals row [40, 60, 50]

  @needs_numpy
  Scenario: groupsummary computes the mean per group
    Given a fresh session
    When I evaluate "T = table([1;2;1], [10;20;30], 'VariableNames', {'g','x'}); S = groupsummary(T, 'g', 'mean', 'x'); v = S.mean_x';"
    Then variable "v" equals row [20, 20]
