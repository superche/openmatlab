Feature: core math, statistics, random numbers (Epic #534)
  @needs_numpy
  Scenario: number theory
    Given a fresh session
    When I evaluate "g = gcd(12, 18); l = lcm(4, 6); p = primes(10); f = factor(84);"
    Then variable "g" equals row [6]
    And variable "l" equals row [12]
    And variable "p" equals row [2, 3, 5, 7]
    And variable "f" equals row [2, 2, 3, 7]

  @needs_numpy
  Scenario: statistics along dimensions
    Given a fresh session
    When I evaluate "m = median([1 2; 3 4]); v = var([1 2 3 4]); s = std([1 1 1]);"
    Then variable "m" equals row [2, 3]
    And variable "s" equals row [0]

  @needs_numpy
  Scenario: rand matches the MATLAB default stream
    Given a fresh session
    When I evaluate "rng('default'); r = round(rand(1, 3) * 1e4);"
    Then variable "r" equals row [8147, 9058, 1270]

  @needs_numpy
  Scenario: differences and rounding
    Given a fresh session
    When I evaluate "d = diff([1 4 9 16]); r = round(pi, 3); x = fix(-2.7); q = rem(-7, 3);"
    Then variable "d" equals row [3, 5, 7]
    And variable "r" equals row [3.142]
    And variable "x" equals row [-2]
    And variable "q" equals row [-1]

  @needs_numpy
  Scenario: polynomials and filters
    Given a fresh session
    When I evaluate "c = conv([1 1], [1 -1]); y = polyval([1 0 -1], 3); z = filter(1, [1 -0.5], [1 0 0]);"
    Then variable "c" equals row [1, 0, -1]
    And variable "y" equals row [8]
    And variable "z" equals row [1, 0.5, 0.25]
