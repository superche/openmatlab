Feature: integer classes, string class, char indexing (Epic #457)
  @needs_numpy
  Scenario: integer arithmetic saturates
    Given a fresh session
    When I evaluate "x = uint8(250) + 10; y = int8(-3.5); k = isinteger(x);"
    Then variable "x" equals row [255]
    And variable "y" equals row [-4]
    And variable "k" equals row [1]

  @needs_numpy
  Scenario: constructors take a class or a like prototype
    Given a fresh session
    When I evaluate "A = zeros(1, 2, 'int16'); B = ones(1, 2, 'like', A); k = isa(B, 'int16');"
    Then variable "k" equals row [1]

  @needs_numpy
  Scenario: string scalars concatenate with plus
    Given a fresh session
    When I evaluate "s = string('ab') + string('cd'); n = strlength(s); z = size(s);"
    Then variable "n" equals row [4]
    And variable "z" equals row [1, 1]

  @needs_numpy
  Scenario: char vectors index like arrays
    Given a fresh session
    When I evaluate "s = 'hello'; s(1) = 'J'; d = double(s(1:2));"
    Then variable "d" equals row [74, 101]
