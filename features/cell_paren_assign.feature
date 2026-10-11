Feature: cell paren assign
  @needs_numpy
  Scenario: replace a cell via parentheses
    Given a fresh session
    When I evaluate "c = {1, 2, 3}; c(2) = {9}; x = c{2};"
    Then variable "x" equals scalar 9
