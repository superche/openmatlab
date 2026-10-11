Feature: Matrix constructors and shape queries
  As a matrix-first user
  I want zeros/ones/eye/size builtins
  So I can build and inspect matrices without literals

  @needs_numpy
  Scenario: size of an identity matrix
    Given a fresh session
    When I evaluate "[m, n] = size(eye(3, 4));"
    Then variable "m" equals 3
    And variable "n" equals 4
