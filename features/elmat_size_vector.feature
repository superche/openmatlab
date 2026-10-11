Feature: size-vector zeros
  @needs_numpy
  Scenario: zeros([m n]) is m-by-n
    Given a fresh session
    When I evaluate "A = zeros([2 3]);"
    Then variable "A" has shape 2 by 3
