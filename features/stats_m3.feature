Feature: Descriptive statistics (Epic #628)
  @needs_numpy
  Scenario: quantiles use the MATLAB method
    When I evaluate "r = [quantile([2 4 6 8 10], 0.5) prctile([2 4 6 8 10], 25)];"
    Then variable "r" equals row [6, 3.5]

  @needs_numpy
  Scenario: moving mean shrinks at the endpoints and histc counts bins
    When I evaluate "r = [movmean([1 2 3 4 5], 3) histc([1 2 2 3 5], 1:5)];"
    Then variable "r" equals row [1.5, 2, 3, 4, 4.5, 1, 2, 1, 0, 1]
