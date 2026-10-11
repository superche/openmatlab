Feature: continue in loops
  @needs_numpy
  Scenario: skip an iteration in for
    Given a fresh session
    When I evaluate "s = 0; for i = 1:4; if i == 2; continue; end; s = s + i; end;"
    Then variable "s" equals 8
