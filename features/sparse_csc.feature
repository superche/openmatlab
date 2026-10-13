Feature: compressed sparse storage (Epic #520)
  @needs_numpy
  Scenario: huge sparse matrices in bounded memory
    Given a fresh session
    When I evaluate "S = sparse(100000, 100000); E = speye(100000); n = nnz(E); z = size(S); S(5, 7) = 3; k = nnz(S);"
    Then variable "n" equals row [100000]
    And variable "z" equals row [100000, 100000]
    And variable "k" equals row [1]

  @needs_numpy
  Scenario: native kernels keep MATLAB results
    Given a fresh session
    When I evaluate "A = sparse([4 1 0; 1 3 1; 0 1 2]); y = (A * [1; 2; 3])'; s = full(sum(A)); B = A' - A; nb = nnz(B); c = full(max(-A));"
    Then variable "y" equals row [6, 10, 8]
    And variable "s" equals row [5, 5, 3]
    And variable "nb" equals row [0]
    And variable "c" equals row [0, -1, 0]

  @needs_numpy
  Scenario: indexing, deletion and concatenation stay sparse
    Given a fresh session
    When I evaluate "S = sparse([1 0 2; 0 3 0]); S(:, 2) = []; T = [S; S]; v = full(T(:))'; k = issparse(T(:));"
    Then variable "v" equals row [1, 0, 1, 0, 2, 0, 2, 0]
    And variable "k" equals row [1]
