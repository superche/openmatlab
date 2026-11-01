Feature: missing values on the analyst path (Epic #1033)
  @needs_numpy
  Scenario: previous fill on a row vector
    Given a fresh session
    When I evaluate "F = fillmissing([1 3 NaN 4 NaN NaN 5], 'previous');"
    Then variable "F" equals row [1, 3, 3, 4, 4, 4, 5]

  @needs_numpy
  Scenario: next fill replaces a leading gap and keeps a trailing one
    Given a fresh session
    When I evaluate "F = fillmissing([NaN 1 NaN 3], 'next');"
    Then variable "F" equals row [1, 1, 3, 3]

  @needs_numpy
  Scenario: constant fill uses one value per column
    Given a fresh session
    When I evaluate "F = fillmissing([1 NaN; NaN 2], 'constant', [100 1000]); c1 = F(:,1)'; c2 = F(:,2)';"
    Then variable "c1" equals row [1, 100]
    And variable "c2" equals row [1000, 2]

  @needs_numpy
  Scenario: ismissing, previous, and rmmissing on a numeric table
    Given a fresh session
    When I evaluate "T = table([1; NaN; 3], [10; 20; NaN], 'VariableNames', {'a','b'}); m = double(ismissing(T)); P = fillmissing(T, 'previous'); R = rmmissing(T); pa = P.a'; pb = P.b'; ra = R.a'; h = height(R);"
    Then variable "m" equals row [0, 0, 1, 0, 0, 1]
    And variable "pa" equals row [1, 1, 3]
    And variable "pb" equals row [10, 20, 20]
    And variable "ra" equals row [1]
    And variable "h" equals row [1]

  @needs_numpy
  Scenario: a logical vector has no missing values
    Given a fresh session
    When I evaluate "a = [true false true]; m = double(ismissing(a)); r = double(rmmissing(a)); f = double(fillmissing(a, 'constant', false)); s = [m r f];"
    Then variable "s" equals row [0, 0, 0, 1, 0, 1, 1, 0, 1]
