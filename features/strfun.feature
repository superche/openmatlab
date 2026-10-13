Feature: core string functions (Epic #536)
  @needs_numpy
  Scenario: find substrings
    Given a fresh session
    When I evaluate "f = strfind('abcabc', 'bc');"
    Then variable "f" equals row [2, 5]

  @needs_numpy
  Scenario: parse numbers from text
    Given a fresh session
    When I evaluate "v = str2num('[1 2 3]'); h = hex2dec('FF'); b = bin2dec('1010');"
    Then variable "v" equals row [1, 2, 3]
    And variable "h" equals row [255]
    And variable "b" equals row [10]

  @needs_numpy
  Scenario: split and join round trip
    Given a fresh session
    When I evaluate "n = numel(strsplit('1-2-3', '-')); ok = strcmp(strjoin(strsplit('1-2-3', '-'), '+'), '1+2+3');"
    Then variable "n" equals row [3]
    And variable "ok" equals row [1]
