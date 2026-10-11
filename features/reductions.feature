Feature: Reductions
  As a matrix-first user
  I want sum/max over vectors and matrices
  So I can summarize data MATLAB-style

  @needs_numpy
  Scenario: index of the maximum
    Given a fresh session
    When I evaluate "[m, i] = max([4 1 8 3]);"
    Then variable "m" equals 8
    And variable "i" equals 3

  @needs_numpy
  Scenario: column sums of a matrix then total
    Given a fresh session
    When I evaluate "t = sum(sum([1 2; 3 4]));"
    Then variable "t" equals 10
