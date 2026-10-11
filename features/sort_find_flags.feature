Feature: sort descend and find last
  @needs_numpy
  Scenario: descending sort
    Given a fresh session
    When I evaluate "b = sort([3 1 2], 'descend');"
    Then variable "b" equals row [3, 2, 1]

  @needs_numpy
  Scenario: last k nonzeros
    Given a fresh session
    When I evaluate "f = find([0 1 1 0 1], 2, 'last');"
    Then variable "f" equals row [3, 5]
