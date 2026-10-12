Feature: MATLAB-aligned Workbench
  As a scientific user
  I want a Host-owned MATLAB-like desktop layout
  So I can evaluate code in a Command Window without forking the shell

  Scenario: Workbench lists host layout regions
    Given a fresh workbench
    When I list workbench regions
    Then the region list includes "command_window"
    And the region "command_window" status is "ready"
    And the region "editor" status is "stub"

  Scenario: Command Window evaluates an expression
    Given a fresh workbench
    When I evaluate "y = 3+4" in the command window
    Then the command window output contains "y ="
    And the workspace contains "y"
