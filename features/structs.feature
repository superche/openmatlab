Feature: structs (Epic #506)
  @needs_numpy
  Scenario: fields are created, nested and read
    Given a fresh session
    When I evaluate "s.a = 1; s.b.c = 2; f = 'd'; s.(f) = 3; v = [s.a s.b.c s.d];"
    Then variable "v" equals row [1, 2, 3]

  @needs_numpy
  Scenario: struct arrays grow and expand as cs-lists
    Given a fresh session
    When I evaluate "s = struct('a', {4, 5}); s(4).a = 7; n = size(s); v = [s.a];"
    Then variable "n" equals row [1, 4]
    And variable "v" equals row [4, 5, 7]

  @needs_numpy
  Scenario: field functions
    Given a fresh session
    When I evaluate "s = struct('b', 1, 'a', 2); k = isfield(s, {'a', 'z'}); t = rmfield(s, 'a'); n = numel(fieldnames(t)); i = isstruct(t);"
    Then variable "k" equals row [1, 0]
    And variable "n" equals row [1]
    And variable "i" equals row [1]
