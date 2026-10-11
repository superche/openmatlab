Feature: end in indexing
  @needs_numpy
  Scenario: A(end) is last linear element
    Given a fresh session
    When I evaluate "A = [10 20 30]; x = A(end);"
    Then variable "x" equals 30
