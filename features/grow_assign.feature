Feature: grow on assign
  @needs_numpy
  Scenario: extend a row past numel
    Given a fresh session
    When I evaluate "v = [1 2]; v(4) = 7;"
    Then variable "v" equals row [1, 2, 0, 7]
