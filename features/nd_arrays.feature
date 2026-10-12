Feature: N-D arrays (Epic #440)
  @needs_numpy
  Scenario: build and query a 3-D array
    Given a fresh session
    When I evaluate "A = zeros(2,3,4); s = size(A); n = ndims(A);"
    Then variable "s" equals row [2, 3, 4]
    And variable "n" equals row [3]

  @needs_numpy
  Scenario: read with three subscripts and end
    Given a fresh session
    When I evaluate "A = reshape(1:8, 2, 2, 2); x = A(2,1,2); y = A(end,end,end);"
    Then variable "x" equals row [6]
    And variable "y" equals row [8]

  @needs_numpy
  Scenario: grow a 2-D matrix into a third page
    Given a fresh session
    When I evaluate "B = ones(2); B(:,:,2) = 5; s = size(B);"
    Then variable "s" equals row [2, 2, 2]

  @needs_numpy
  Scenario: reduce along the third dimension
    Given a fresh session
    When I evaluate "A = reshape(1:8, 2, 2, 2); s = sum(A, 3); r = s(:)';"
    Then variable "r" equals row [6, 8, 10, 12]

  @needs_numpy
  Scenario: logical mask over an N-D array
    Given a fresh session
    When I evaluate "A = reshape(1:8, 2, 2, 2); x = A(A > 6)';"
    Then variable "x" equals row [7, 8]
