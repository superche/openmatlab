Feature: array builders, sets and sorting (Epic #535)
  @needs_numpy
  Scenario: replicate and grid
    Given a fresh session
    When I evaluate "a = repmat([1 2], 1, 2); [X, Y] = meshgrid(1:2, 1:1);"
    Then variable "a" equals row [1, 2, 1, 2]
    And variable "X" equals row [1, 2]

  @needs_numpy
  Scenario: set operations
    Given a fresh session
    When I evaluate "u = union([3 1], [2 1]); i = intersect([1 2 3 4], [3 4 5]); d = setdiff([5 1 3 1], 1);"
    Then variable "u" equals row [1, 2, 3]
    And variable "i" equals row [3, 4]
    And variable "d" equals row [3, 5]

  @needs_numpy
  Scenario: stable unique and membership
    Given a fresh session
    When I evaluate "s = unique([3 1 2 3], 'stable'); [tf, loc] = ismember([1 5 2], [2 1 1 9]);"
    Then variable "s" equals row [3, 1, 2]
    And variable "loc" equals row [2, 0, 1]

  @needs_numpy
  Scenario: sortrows descending on a column
    Given a fresh session
    When I evaluate "b = sortrows([1 2; 1 1; 0 5], -2); c = b(:, 2)';"
    Then variable "c" equals row [5, 2, 1]
