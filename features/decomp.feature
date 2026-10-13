Feature: dense decompositions (Epic #538)
  @needs_numpy
  Scenario: symmetric eigenvalues come back ascending
    Given a fresh session
    When I evaluate "e = eig([2 1; 1 2])';"
    Then variable "e" equals row [1, 3]

  @needs_numpy
  Scenario: Cholesky factor and trace
    Given a fresh session
    When I evaluate "R = chol([4 0; 0 9]); d = diag(R)'; t = trace(magic(3));"
    Then variable "d" equals row [2, 3]
    And variable "t" equals row [15]
