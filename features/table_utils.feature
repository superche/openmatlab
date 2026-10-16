Feature: table utilities, sorting and sets (Epic #693)
  @needs_numpy
  Scenario: sort a table by one variable
    Given a fresh session
    When I evaluate "T = table([3;1;2], {'c';'a';'b'}, 'VariableNames', {'n','s'}); S = sortrows(T, 'n'); v = S.n';"
    Then variable "v" equals row [1, 2, 3]

  @needs_numpy
  Scenario: varfun names outputs after the function
    Given a fresh session
    When I evaluate "T = table([1;2;3], [4;5;6], 'VariableNames', {'a','b'}); V = varfun(@sum, T); v = V.sum_b;"
    Then variable "v" equals row [15]

  @needs_numpy
  Scenario: unique rows of a table
    Given a fresh session
    When I evaluate "U = unique(table([1;1;2], [5;5;6])); v = height(U);"
    Then variable "v" equals row [2]

  @needs_numpy
  Scenario: table2array concatenates variables
    Given a fresh session
    When I evaluate "v = reshape(table2array(table([1;2], [3;4])), 1, []);"
    Then variable "v" equals row [1, 2, 3, 4]
