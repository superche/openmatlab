Feature: findgroups IncludeMissing, splitapply tables, groupcounts, grouptransform, groupfilter
  #1054 and #1055. Values are the public examples or the formulas those pages name.

  @needs_numpy
  Scenario: IncludeMissing numbers the missing group and returns it in the id
    Given a fresh grouping session
    When I run "v = findgroups([1;NaN;2], 'IncludeMissing', true)';"
    Then "v" is close to [1, 3, 2]

  @needs_numpy
  Scenario: splitapply stacks one table row from each group
    Given a fresh grouping session
    When I run "G = findgroups([1;1;2;2]); S = splitapply(@(x) table(sum(x), 'VariableNames', {'total'}), [10;20;30;40], G); v = S.total';"
    Then "v" is close to [30, 70]

  @needs_numpy
  Scenario: groupcounts on a vector returns the sorted counts
    Given a fresh grouping session
    When I run "[B,BG] = groupcounts([1;1;2;2;3;5;3;3;1;4]); v = [B' BG'];"
    Then "v" is close to [3, 2, 3, 1, 1, 1, 2, 3, 4, 5]

  @needs_numpy
  Scenario: groupcounts IncludeEmptyGroups keeps a zero logical group
    Given a fresh grouping session
    When I run "[B,BG] = groupcounts([true;true], 'IncludeEmptyGroups', true); v = [double(BG') B'];"
    Then "v" is close to [0, 1, 0, 2]

  @needs_numpy
  Scenario: grouptransform rescales each group onto zero to one
    Given a fresh grouping session
    When I run "v = grouptransform([10;30;20;40], [1;1;2;2], 'rescale')';"
    Then "v" is close to [0, 1, 0, 1]

  @needs_numpy
  Scenario: groupfilter keeps the group whose sample count is greater than two
    Given a fresh grouping session
    When I run "T = table([1;1;1;2;2;3], [3;1;2;9;8;5], 'VariableNames', {'g','x'}); G = groupfilter(T, 'g', @(x) numel(x) > 2); v = G.x';"
    Then "v" is close to [3, 1, 2]
