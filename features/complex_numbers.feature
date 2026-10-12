Feature: complex numbers (Epic #449)
  @needs_numpy
  Scenario: imaginary literal arithmetic
    Given a fresh session
    When I evaluate "z = (3+4i)*(1-2i); r = real(z); m = imag(z);"
    Then variable "r" equals row [11]
    And variable "m" equals row [-2]

  @needs_numpy
  Scenario: square root of a negative number is imaginary
    Given a fresh session
    When I evaluate "z = sqrt(-9); m = imag(z); r = isreal(z);"
    Then variable "m" equals row [3]
    And variable "r" equals row [0]

  @needs_numpy
  Scenario: fractional matrix power with a complex result
    Given a fresh session
    When I evaluate "A = [-1 0; 0 4]^0.5; d = imag([A(1,1) A(2,2)]);"
    Then variable "d" equals row [1, 0]

  @needs_numpy
  Scenario: magnitude and conjugate transpose
    Given a fresh session
    When I evaluate "z = [3+4i 1i]'; a = abs(z)'; i2 = imag(z)';"
    Then variable "a" equals row [5, 1]
    And variable "i2" equals row [-4, -1]
