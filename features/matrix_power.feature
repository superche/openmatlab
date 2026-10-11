Feature: scalar power
  @needs_numpy
  Scenario: i^2 in a loop sum
    Given a fresh session
    When I evaluate "x = 0; for i = 1:3; x = x + i^2; end"
    Then variable "x" equals 14
