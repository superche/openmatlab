Feature: Script .m files
  As a user
  I want statement-only .m scripts
  So I can initialize workspaces without functions

  @needs_numpy
  Scenario: eval script sets variables
    Given a session and script file setting a and b
    When I evaluate that script
    Then variable "b" equals 15
