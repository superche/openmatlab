Feature: sort
  @needs_numpy
  Scenario: sort a row ascending
    Given a fresh session
    When I evaluate "y = sort([3 1 4 2]);"
    Then variable "y" first equals 1
