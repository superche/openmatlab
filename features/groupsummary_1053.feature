Feature: groupsummary bins and array input (issue #1053)
  @needs_numpy
  Scenario: bin edges keep the published mean of profit
    Given a fresh analyst session
    When I run "ItemsSold = [14;13;8;5;10;16;8;6;7;11]; Profit = [2032;3071;1185;2587;1998;2899;3112;909;2619;3085]; T = table(ItemsSold, Profit); S = groupsummary(T, 'ItemsSold', [0 4 8 12 16], 'mean', 'Profit'); v = S.mean_Profit';"
    Then "v" is close to [2038.33333333333, 2345, 2667.33333333333]

  @needs_numpy
  Scenario: array groupsummary returns the sum, the groups, and the counts
    Given a fresh analyst session
    When I run "[B,BG,BC] = groupsummary([10;20;30;40], [1;1;2;2], 'sum'); v = [B' BG' BC'];"
    Then "v" is close to [30, 70, 1, 2, 2, 2]

  @needs_numpy
  Scenario: noprefix keeps the data variable name
    Given a fresh analyst session
    When I run "T = table([1;1;2], [10;30;20], 'VariableNames', {'g','x'}); S = groupsummary(T, 'g', 'sum', 'x', 'VariableNamingRule', 'noprefix'); v = S.x';"
    Then "v" is close to [40, 20]
