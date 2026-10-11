Feature: 2-D logical indexing
  @needs_numpy
  Scenario: select a row by logical mask
    Given a fresh session
    When I evaluate "A = [1 2 3; 4 5 6]; L = [1; 0] > 0; r = A(L, :);"
    Then variable "r" equals row [1, 2, 3]
