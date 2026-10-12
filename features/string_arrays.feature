Feature: string arrays and string methods (Epic #482)
  @needs_numpy
  Scenario: brackets build a string array
    Given a fresh session
    When I evaluate "s = ["a" "bc"; "d" "e"]; z = size(s); k = isstring(s); n = strlength(s(1,:));"
    Then variable "z" equals row [2, 2]
    And variable "k" equals row [1]
    And variable "n" equals row [1, 2]

  @needs_numpy
  Scenario: assignment grows with missing and deletes
    Given a fresh session
    When I evaluate "s = ["a" "b"]; s(4) = "d"; s(1) = []; z = size(s);"
    Then variable "z" equals row [1, 3]

  @needs_numpy
  Scenario: elementwise plus and comparison
    Given a fresh session
    When I evaluate "s = ["a" "b"] + "x"; e = s == "bx";"
    Then variable "e" equals row [0, 1]

  @needs_numpy
  Scenario: text methods work on strings and chars
    Given a fresh session
    When I evaluate "p = split("a,b,c", ","); n = numel(p); c = contains(upper(p), "B"); t = strcmp(strtrim(' x '), 'x');"
    Then variable "n" equals row [3]
    And variable "c" equals row [0, 1, 0]
    And variable "t" equals row [1]
