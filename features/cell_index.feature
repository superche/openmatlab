Feature: Cell content indexing
  As a MATLAB-compatible user
  I want c{i,j} content indexing
  So I can extract mixed cell contents

  @needs_numpy
  Scenario: read char from a cell
    Given a fresh session
    When I evaluate "c = {1, 'z'}; s = c{1,2};"
    Then char variable "s" equals "z"
