Feature: splines, interpolation and polynomial calculus (Epic #626)
  @needs_numpy
  Scenario: a not-a-knot spline reproduces a cubic and ppval evaluates it
    When I evaluate "pp = spline(0:3, (0:3).^3); r = [ppval(pp, 1.5) spline(0:3, (0:3).^3, 2.5)];"
    Then variable "r" equals row [3.375, 15.625]

  @needs_numpy
  Scenario: polynomial derivative and integral round-trip
    When I evaluate "p = [3 2 1]; r = polyder(polyint(p));"
    Then variable "r" equals row [3, 2, 1]
