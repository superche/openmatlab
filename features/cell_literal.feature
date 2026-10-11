Feature: Cell array literals
  As a MATLAB-compatible user
  I want {a,b;c,d} cell literals
  So I can group mixed values

  @needs_numpy
  Scenario: mixed numeric and char cells
    Given a fresh session
    When I evaluate "c = {1, 'z'};"
    Then cell "c" has shape 1 by 2
