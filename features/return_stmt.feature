Feature: return in functions
  @needs_numpy
  Scenario: early return skips later assignments
    Given a fresh session with early.m on path
    When I evaluate "y = early(2);"
    Then variable "y" equals 3
