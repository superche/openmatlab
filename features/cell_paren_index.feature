Feature: Parentheses cell indexing
  @needs_numpy
  Scenario: c(i,j) returns a 1x1 cell
    Given a fresh session
    When I evaluate "c = {1, 'z'}; b = c(1,2); x = b{1};"
    Then char variable "x" equals "z"
