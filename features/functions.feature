Feature: functions, variadic arguments, globals and eval (Epic #531)
  @needs_numpy
  Scenario: varargin and nargin
    Given a fresh session
    When I evaluate "f = str2func('@(varargin) numel(varargin)'); g = feval(@plus, 2, 3);"
    Then variable "g" equals row [5]

  @needs_numpy
  Scenario: eval with a catch string
    Given a fresh session
    When I evaluate "eval('x = 2 * 21;'); eval('bad syntax (', 'y = 1;');"
    Then variable "x" equals row [42]
    And variable "y" equals row [1]

  @needs_numpy
  Scenario: operator functions match operators
    Given a fresh session
    When I evaluate "a = plus([1 2], 3); b = mtimes([1 2], [3; 4]); c = ge(2, [1 2 3]);"
    Then variable "a" equals row [4, 5]
    And variable "b" equals row [11]
    And variable "c" equals row [1, 1, 0]

  @needs_numpy
  Scenario: global in the base workspace
    Given a fresh session
    When I evaluate "global G; G = 4; global G; h = G + 1;"
    Then variable "h" equals row [5]

  @needs_numpy
  Scenario: exist classifies names
    Given a fresh session
    When I evaluate "v = 1; a = exist('v'); b = exist('sum'); c = exist('no_such_thing_531');"
    Then variable "a" equals row [1]
    And variable "b" equals row [5]
    And variable "c" equals row [0]
