Feature: Sparse maturity (Epic #631)
  @needs_numpy
  Scenario: mostly-true comparisons and not stay sparse
    When I evaluate "S = speye(3); r = [issparse(S == 0) issparse(~S) issparse(S <= 0.5) nnz(~S)];"
    Then variable "r" equals row [1, 1, 1, 6]

  @needs_numpy
  Scenario: kron of sparse stays sparse
    When I evaluate "A = sparse([4 1 0; 1 4 1; 0 1 4]); r = [issparse(kron(speye(2), A)) nnz(kron(speye(2), A))];"
    Then variable "r" equals row [1, 14]
