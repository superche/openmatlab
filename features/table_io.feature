Feature: readtable and writetable (Epic #694)
  @needs_numpy
  Scenario: write a table and read it back
    Given a fresh session
    When I evaluate "f = [tempname '.csv']; writetable(table([1;2;3], [4;5;6], 'VariableNames', {'a','b'}), f); R = readtable(f); v = R.b';"
    Then variable "v" equals row [4, 5, 6]

  @needs_numpy
  Scenario: missing numeric field becomes NaN
    Given a fresh session
    When I evaluate "f = [tempname '.csv']; writecell({'x','y';1,'a';[],'b';3,'c'}, f); T = readtable(f); n = double(isnan(T.x'));"
    Then variable "n" equals row [0, 1, 0]

  @needs_numpy
  Scenario: readcell keeps numbers numeric
    Given a fresh session
    When I evaluate "f = [tempname '.csv']; writecell({1,'a';2,'b'}, f); C = readcell(f); v = C{2,1};"
    Then variable "v" equals row [2]
