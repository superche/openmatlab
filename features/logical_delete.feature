Feature: logical-mask delete
  @needs_numpy
  Scenario: drop elements where mask is true
    Given a fresh session
    When I evaluate "v = [5 1 6 2]; v(v > 3) = [];"
    Then variable "v" equals row [1, 2]
