Feature: cellfun
  @needs_numpy
  Scenario: numel over a cell row
    Given a fresh session
    When I evaluate "c = {[1 2], [3 4 5], 6}; n = cellfun(@numel, c);"
    Then variable "n" equals row [2, 3, 1]
