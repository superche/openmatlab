Feature: range indexed assignment
  @needs_numpy
  Scenario: linear range with vector RHS
    Given a fresh session
    When I evaluate "A = [1 2 3 4]; A(1:3) = [10 20 30]; B = A;"
    Then variable "B" equals row [10, 20, 30, 4]
