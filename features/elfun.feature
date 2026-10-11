Feature: Elementwise math
  As a matrix-first user
  I want MATLAB-like rounding and mod
  So numeric results match published semantics

  @needs_numpy
  Scenario: round half away from zero
    Given a fresh session
    When I evaluate "r = round(2.5);"
    Then variable "r" equals 3

  @needs_numpy
  Scenario: mod with negative dividend
    Given a fresh session
    When I evaluate "m = mod(-5, 3);"
    Then variable "m" equals 1
