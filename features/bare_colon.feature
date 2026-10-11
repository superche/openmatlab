Feature: bare colon indexing
  @needs_numpy
  Scenario: A(1,:) is a row
    Given a fresh session
    When I evaluate "A = [1 2 3; 4 5 6]; B = A(1,:);"
    Then variable "B" equals row [1, 2, 3]
