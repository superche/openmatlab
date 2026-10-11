Feature: Plot MVP
  As an interactive user
  I want plot(x, y) from the REPL language
  So that I can try and tweak visually

  @needs_numpy @needs_matplotlib
  Scenario: Builtin plot creates a line
    Given a fresh plotting session
    When I evaluate "plot(1:5, 1:5);"
    Then the last figure has 1 line
