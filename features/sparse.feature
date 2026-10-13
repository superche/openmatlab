Feature: sparse matrices (Epic #487)
  @needs_numpy
  Scenario: triplet construction adds duplicates
    Given a fresh session
    When I evaluate "S = sparse([1 1 2], [1 1 3], [2 3 4]); n = nnz(S); k = issparse(S); v = nonzeros(S)';"
    Then variable "n" equals row [2]
    And variable "k" equals row [1]
    And variable "v" equals row [5, 4]

  @needs_numpy
  Scenario: sparsity follows MATLAB rules
    Given a fresh session
    When I evaluate "S = speye(2); a = issparse(S * 3); b = issparse(S + 1); c = issparse(S .* [1 2; 3 4]); d = issparse(S ^ 2);"
    Then variable "a" equals row [1]
    And variable "b" equals row [0]
    And variable "c" equals row [1]
    And variable "d" equals row [1]

  @needs_numpy
  Scenario: full converts back
    Given a fresh session
    When I evaluate "F = full(sparse(2, 1, 7)); k = issparse(F);"
    Then variable "F" equals row [0, 7]
    And variable "k" equals row [0]
