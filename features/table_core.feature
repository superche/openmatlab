Feature: table core (Epic #691)
  @needs_numpy
  Scenario: build a table and read a variable
    Given a fresh session
    When I evaluate "a = [1;2;3]; b = [4;5;6]; T = table(a, b); v = T.b'; h = height(T);"
    Then variable "v" equals row [4, 5, 6]
    And variable "h" equals row [3]

  @needs_numpy
  Scenario: logical row selection and brace extraction
    Given a fresh session
    When I evaluate "T = table([1;2;3], [4;5;6], 'VariableNames', {'a','b'}); R = T(T.a > 1, :); v = R{:, 'b'}';"
    Then variable "v" equals row [5, 6]

  @needs_numpy
  Scenario: vertical concatenation
    Given a fresh session
    When I evaluate "T = table([1;2]); U = [T; T]; v = U.Var1';"
    Then variable "v" equals row [1, 2, 1, 2]
