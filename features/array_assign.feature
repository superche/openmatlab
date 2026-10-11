Feature: Indexed array assignment
  @needs_numpy
  Scenario: set a matrix entry
    Given a fresh session
    When I evaluate "A = [1 2; 3 4]; A(1,2) = 9; x = A(1,2);"
    Then variable "x" equals 9
