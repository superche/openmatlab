Feature: JSON and delimited numeric I/O (Epic #629)
  @needs_numpy
  Scenario: jsondecode consolidates arrays and jsonencode round-trips
    When I evaluate "q = char(34); s = jsondecode(['{' q 'b' q ':[1,2,3]}']); r = [s.b' strcmp(jsonencode(struct('a', 1, 'b', [1 2])), ['{' q 'a' q ':1,' q 'b' q ':[1,2]}'])];"
    Then variable "r" equals row [1, 2, 3, 1]

  @needs_numpy
  Scenario: dlmwrite appends and dlmread reads back
    When I evaluate "f = [tempname '.txt']; dlmwrite(f, [1 2 3], ';'); dlmwrite(f, [4 5 6], '-append', 'delimiter', ';'); m = dlmread(f, ';'); r = m(:)'; delete(f);"
    Then variable "r" equals row [1, 4, 2, 5, 3, 6]
