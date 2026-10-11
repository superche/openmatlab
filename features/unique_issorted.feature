Feature: unique and issorted
  @needs_numpy
  Scenario: unique sorts and dedupes a row
    Given a fresh session
    When I evaluate "u = unique([3 1 3 2]);"
    Then variable "u" equals row [1, 2, 3]
