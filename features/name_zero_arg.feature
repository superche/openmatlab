Feature: bare NaN Inf pi
  @needs_numpy
  Scenario: NaN in matrix for max omitnan
    Given a fresh session
    When I evaluate "m = max([1 NaN 3]);"
    Then variable "m" equals 3
