Feature: Evaluator and display
  As an interactive user
  I want openmatlab -e to compute matrices
  So that try/tweak works before plotting

  @needs_numpy
  Scenario: Evaluate arithmetic into ans
    Given a fresh session
    When I evaluate "1 + 2 * 3"
    Then variable "ans" has shape 1 by 1
    And ans equals 7

  @needs_numpy
  Scenario: Assignment with suppress
    Given a fresh session
    When I evaluate "a = [1 2; 3 4];"
    Then variable "a" has shape 2 by 2
