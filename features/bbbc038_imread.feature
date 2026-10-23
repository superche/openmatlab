Feature: PNG imread for one BBBC038-style FOV (Epic #1020)
  @needs_numpy
  Scenario: an 8-bit grayscale PNG loads as uint8
    Given a 2 by 2 grayscale png
    When I evaluate the png "I = imread(png); h = size(I, 1); w = size(I, 2); c = size(I, 3); k = double(strcmp(class(I), 'uint8')); p = double(I(1, :));"
    Then the png variable "h" equals row [2]
    And the png variable "w" equals row [2]
    And the png variable "c" equals row [1]
    And the png variable "k" equals row [1]
    And the png variable "p" equals row [10, 20]

  Scenario: an RGBA PNG returns RGB and a separate alpha
    Given a 1 by 1 rgba png
    When I evaluate the png "[A, map, alpha] = imread(png); p = double(A(1, 1, :)); q = double(alpha); nmap = numel(map);"
    Then the png variable "p" equals row [9, 8, 7]
    And the png variable "q" equals row [6]
    And the png variable "nmap" equals row [0]
