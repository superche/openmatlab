Feature: Multi-return assignment
  As a user
  I want [a, b] = f(...)
  So that .m functions with multiple outputs work

  @needs_numpy
  Scenario: swap two values
    Given a temp toolbox with swap.m
    When I addpath that toolbox
    And I evaluate "[u, v] = swap(3, 4);"
    Then variable "u" equals 4
    And variable "v" equals 3
