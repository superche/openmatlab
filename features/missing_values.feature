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

  @needs_numpy
  Scenario: a char blank is missing and stays char through remove and fill
    Given a fresh session
    When I evaluate "m = double(ismissing('a b')); r = double(rmmissing('a b')); p = double(fillmissing('a b', 'previous')); n = double(fillmissing('a b', 'next')); c = double(fillmissing('a b', 'constant', 'x')); s = [m r p n c];"
    Then variable "s" equals row [0, 1, 0, 97, 98, 97, 97, 98, 97, 98, 98, 97, 120, 98]

  @needs_numpy
  Scenario: rmmissing of a blank char keeps the empty shape
    Given a fresh session
    When I evaluate "a = size(rmmissing('   ')); b = size(rmmissing(['a ';'  '])); c = size(''); s = [a b c];"
    Then variable "s" equals row [1, 0, 0, 2, 0, 0]

  @needs_numpy
  Scenario: indexing a char keeps an empty shape
    Given a fresh session
    When I evaluate "x = 'abc'; y = ['ab'; 'cd']; s = [size(x(:,[])) size(x([],:)) size(y(:,[])) size(y([],:)) size(char(zeros(0,3))) size(blanks(0))];"
    Then variable "s" equals row [1, 0, 0, 3, 2, 0, 0, 2, 0, 3, 1, 0]

  @needs_numpy
  Scenario: empty arrays and a 0-row table keep their shape
    Given a fresh session
    When I evaluate "a = rmmissing([]); b = rmmissing(zeros(0,3)); c = rmmissing(zeros(1,0)); ia = ismissing([]); ib = ismissing(zeros(0,3)); ic = ismissing(zeros(1,0)); fa = fillmissing([], 'next'); fb = fillmissing(zeros(0,3), 'previous'); fc = fillmissing(zeros(1,0), 'constant', 0); T = table(zeros(0,1), zeros(0,3), 'VariableNames', {'a','b'}); m = ismissing(T); R = rmmissing(T); F = fillmissing(T, 'next'); s = [size(a) size(b) size(c) size(ia) size(ib) size(ic) size(fa) size(fb) size(fc) size(m) height(R) width(R) height(F) size(F.a)];"
    Then variable "s" equals row [0, 0, 0, 3, 1, 0, 0, 0, 0, 3, 1, 0, 0, 0, 0, 3, 1, 0, 0, 2, 0, 2, 0, 0, 1]

  @needs_numpy
  Scenario: rmmissing along dimension 2 reports a row of removed columns
    Given a fresh session
    When I evaluate "A = [1 NaN 3; NaN 5 NaN]; [R, tf] = rmmissing(A, 2); s = [size(tf) double(tf) size(R)];"
    Then variable "s" equals row [1, 3, 1, 1, 1, 2, 0]

  @needs_numpy
  Scenario: a single-row table fills down each variable
    Given a fresh session
    When I evaluate "T = table([NaN 5], 'VariableNames', {'x'}); F = fillmissing(T, 'next'); m = double(ismissing(F.x)); s = [m size(F.x) F.x(2)];"
    Then variable "s" equals row [1, 0, 1, 2, 5]
