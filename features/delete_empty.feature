Feature: delete via empty assign
  @needs_numpy
  Scenario: remove one element from a row
    Given a fresh session
    When I evaluate "v = [1 2 3 4]; v(2) = [];"
    Then variable "v" equals row [1, 3, 4]
