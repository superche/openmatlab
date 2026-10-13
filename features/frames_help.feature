Feature: caller/base workspaces and help browsing (Epic #610)
  @needs_numpy
  Scenario: assignin and evalin reach the base workspace
    Given a fresh session
    When I evaluate "y = 2; assignin('base', 'z', 5); v = evalin('base', 'y + z');"
    Then variable "v" equals row [7]

  @needs_numpy
  Scenario: evalin catch string
    Given a fresh session
    When I evaluate "r = evalin('base', 'missing_zz', '0');"
    Then variable "r" equals row [0]
