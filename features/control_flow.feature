Feature: Minimal control flow
  As a user
  I want if/for
  So I can branch and loop in scripts

  @needs_numpy
  Scenario: for accumulates
    Given a fresh session
    When I evaluate "s = 0;"
    And I evaluate multiline for sum 1 to 3
    Then variable "s" equals 6
