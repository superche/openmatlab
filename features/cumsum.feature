Feature: cumsum
  @needs_numpy
  Scenario: cumulative sum of a row
    Given a fresh session
    When I evaluate "y = cumsum([1 2 3]);"
    Then variable "y" equals 6 at last
