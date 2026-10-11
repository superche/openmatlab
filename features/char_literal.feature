Feature: Single-quote char literals
  As a MATLAB-compatible user
  I want 'char' literals distinct from transpose
  So path and text APIs accept public-doc syntax

  Scenario: escaped quote inside char
    Given a fresh session
    When I evaluate "s = 'a''b';"
    Then char variable "s" equals "a'b"

  @needs_numpy
  Scenario: transpose after matrix still works
    Given a fresh session
    When I evaluate "B = [1 2]';"
    Then variable "B" row count is 2
