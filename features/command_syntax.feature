Feature: command syntax and workspace commands (Epic #532)
  @needs_numpy
  Scenario: clear with names and wildcards
    Given a fresh session
    When I evaluate "a1 = 1; a2 = 2; b = 3; clear a*; n = exist('a1') + exist('a2'); m = exist('b');"
    Then variable "n" equals row [0]
    And variable "m" equals row [1]

  @needs_numpy
  Scenario: a variable name followed by an operator stays an expression
    Given a fresh session
    When I evaluate "a = 3; r = 0; a -1; r = ans;"
    Then variable "r" equals row [2]

  @needs_numpy
  Scenario: format long changes display digits
    Given a fresh session
    When I evaluate "format long; t = numel(strtrim(evalc('disp(pi)'))); format short; u = numel(strtrim(evalc('disp(pi)')));"
    Then variable "t" equals row [17]
    And variable "u" equals row [6]

  @needs_numpy
  Scenario: who returns a cell of names
    Given a fresh session
    When I evaluate "x = 1; y = 2; w = who; n = numel(w); k = iscell(w);"
    Then variable "n" equals row [2]
    And variable "k" equals row [1]

  @needs_numpy
  Scenario: isvarname
    Given a fresh session
    When I evaluate "a = isvarname('ok_1'); b = isvarname('end'); c = isvarname('2x');"
    Then variable "a" equals row [1]
    And variable "b" equals row [0]
    And variable "c" equals row [0]
