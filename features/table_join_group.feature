Feature: joins and grouping (Epic #696, #1052, #1056)
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

  @needs_numpy
  Scenario: KeepOneCopy retains the left copy of a shared non-key
    Given a fresh session
    When I evaluate "A = table([1;2],[10;20],[100;200],'VariableNames',{'k','x','z'}); B = table([2;1],[8;7],[9;6],'VariableNames',{'k','x','z'}); J = join(A, B, 'Keys','k','KeepOneCopy','x'); v = J.x';"
    Then variable "v" equals row [10, 20]

  @needs_numpy
  Scenario: KeepKeys includes the right key aligned to the left rows
    Given a fresh session
    When I evaluate "A = table([1;2],[10;20],'VariableNames',{'k','x'}); B = table([2;1],[8;7],'VariableNames',{'k','y'}); J = join(A, B, 'KeepKeys', true); v = J.y';"
    Then variable "v" equals row [7, 8]

  @needs_numpy
  Scenario: join on row names keeps the left row order
    Given a fresh session
    When I evaluate "A = table([10;30],'VariableNames',{'x'},'RowNames',{'c','a'}); B = table([1;2;3],'VariableNames',{'y'},'RowNames',{'b','a','c'}); J = join(A, B, 'Keys','RowNames'); v = J.y';"
    Then variable "v" equals row [3, 2]

  @needs_numpy
  Scenario: innerjoin matches a cellstr key to a string key
    Given a fresh session
    When I evaluate "A = table({'b';'a'},[1;2],'VariableNames',{'k','x'}); B = table(string({'a';'b'}),[8;9],'VariableNames',{'k','y'}); I = innerjoin(A, B); v = I.x';"
    Then variable "v" equals row [2, 1]

  @needs_numpy
  Scenario: an indexing expression is suffixed left
    Given a fresh session
    When I evaluate "A = table([1;2],[3;4],'VariableNames',{'k','x'}); B = table([2;1],[5;6],'VariableNames',{'k','x'}); J = join(A(1:2,:), B, 'Keys','k'); v = J.Properties.VariableNames;"
    Then variable "v" equals texts [k, x_left, x_B]

  @needs_numpy
  Scenario: joining a table to itself numbers the left suffix
    Given a fresh session
    When I evaluate "A = table([1;2],[3;4],'VariableNames',{'k','x'}); J = join(A, A, 'Keys','k'); v = J.Properties.VariableNames;"
    Then variable "v" equals texts [k, x_A_1, x_A]
