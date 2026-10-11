Feature: logical indexing
  @needs_numpy
  Scenario: select positives
    Given a fresh session
    When I evaluate "v = [5 -1 3 -2]; p = v(v > 0);"
    Then variable "p" equals row [5, 3]
