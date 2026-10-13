Feature: linear solve mldivide/mrdivide (Epic #496)
  @needs_numpy
  Scenario: square system and matrix right division
    Given a fresh session
    When I evaluate "x = [2 0; 0 4] \ [2; 4]; y = [1 2; 3 4] / [1 2; 3 4]; e = round(y(:)');"
    Then variable "x" equals row [1, 1]
    And variable "e" equals row [1, 0, 0, 1]

  @needs_numpy
  Scenario: least squares and basic solution
    Given a fresh session
    When I evaluate "u = [1 2 3] \ 6; l = round(([1 1; 1 2; 1 3] \ [1; 2; 2])' * 6);"
    Then variable "u" equals row [0, 0, 2]
    And variable "l" equals row [4, 3]

  @needs_numpy
  Scenario: singular matrix warns and inv/det/rank work
    Given a fresh session
    When I evaluate "warning('off', 'all'); s = [1 2; 2 4] \ [1; 2]; k = strcmp(lastwarn, 'Matrix is singular to working precision.'); warning('on', 'all'); r = rank([1 2; 2 4]); d = round(det([1 2; 3 4])); I = inv([2 0; 0 4]);"
    Then variable "k" equals row [1]
    And variable "r" equals row [1]
    And variable "d" equals row [-2]
    And variable "I" equals row [0.5, 0, 0, 0.25]
