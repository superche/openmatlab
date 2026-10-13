Feature: FFT family (Epic #625)
  @needs_numpy
  Scenario: spectrum of a pure tone peaks at its bin
    When I evaluate "s = sin(2*pi*(0:15)/16*3); S = abs(fft(s)); r = round([S(4) S(14)]);"
    Then variable "r" equals row [8, 8]

  @needs_numpy
  Scenario: ifft inverts fft and fftshift centres zero frequency
    When I evaluate "x = [4 1 2 3]; r = [real(ifft(fft(x))) fftshift(1:4) nextpow2(9)];"
    Then variable "r" equals row [4, 1, 2, 3, 3, 4, 1, 2, 4]
