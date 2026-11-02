Feature: groupsummary empty groups for the analyst story (M17 #742)
  @needs_numpy
  Scenario: an unused category is an empty group whose sum is zero
    Given a fresh analyst session
    When I run "T = table(categorical({'a';'a';'b'}, {'a','b','c'}), [10;30;20], 'VariableNames', {'g','x'}); S = groupsummary(T, 'g', 'sum', 'x', 'IncludeEmptyGroups', true); v = [S.GroupCount' S.sum_x'];"
    Then "v" is close to [2, 1, 0, 40, 20, 0]

  @needs_numpy
  Scenario: the public categorical-by-logical example counts the two empty combinations
    Given a fresh analyst session
    When I run "HealthStatus = categorical({'Poor';'Good';'Fair';'Fair';'Poor';'Excellent';'Good';'Excellent'}); Smoker = [true;false;false;true;true;false;false;true]; Weight = [176;153;131;133;119;120;140;129]; T = table(HealthStatus, Smoker, Weight); S = groupsummary(T, {'HealthStatus','Smoker'}, 'mean', 'Weight', 'IncludeEmptyGroups', true); v = S.GroupCount';"
    Then "v" is close to [1, 1, 1, 1, 2, 0, 0, 2]

  @needs_numpy
  Scenario: mean skips NaN in the data and GroupCount still counts that row
    Given a fresh analyst session
    When I run "T = table([1;1;1], [2;NaN;4], 'VariableNames', {'g','x'}); S = groupsummary(T, 'g', {'mean','std'}, 'x'); v = [S.mean_x S.std_x S.GroupCount];"
    Then "v" is close to [3, 1.41421356237, 3]

  @needs_numpy
  Scenario: an empty cellstr group key sorts last
    Given a fresh analyst session
    When I run "T = table({'a';'b';''}, [1;2;3]); S = groupsummary(T, 'Var1', 'sum'); v = S.sum_Var2';"
    Then "v" is close to [1, 2, 3]

  @needs_numpy
  Scenario: IncludeMissingGroups false drops an empty cellstr group key
    Given a fresh analyst session
    When I run "T = table({'a';'b';''}, [1;2;3]); S = groupsummary(T, 'Var1', 'sum', 'IncludeMissingGroups', false); v = S.sum_Var2';"
    Then "v" is close to [1, 2]
