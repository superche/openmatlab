Feature: while and break
  As a user
  I want while loops and break
  So I can iterate until a condition

  @needs_numpy
  Scenario: while increments then stops
    Given a fresh session
    When I evaluate "x = 0;"
    And I evaluate while x less than 3 increment
    Then variable "x" equals 3
