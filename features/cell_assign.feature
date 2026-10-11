Feature: Cell content assignment
  @needs_numpy
  Scenario: overwrite a char cell
    Given a fresh session
    When I evaluate "c = {1, 'a'}; c{1,2} = 'b'; x = c{1,2};"
    Then char variable "x" equals "b"
