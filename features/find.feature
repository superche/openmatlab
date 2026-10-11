Feature: find
  @needs_numpy
  Scenario: linear indices of nonzeros
    Given a fresh session
    When I evaluate "i = find([0 4 0 5]);"
    Then variable "i" first equals 2
