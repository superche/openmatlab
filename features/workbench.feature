Feature: MATLAB-aligned Workbench
  As a scientific user
  I want a Host-owned MATLAB-like desktop layout
  So I can evaluate code and browse workspace/files/figures without forking the shell

  Scenario: Workbench lists host layout regions
    Given a fresh workbench
    When I list workbench regions
    Then the region list includes "command_window"
    And the region "command_window" status is "ready"
    And the region "editor" status is "ready"
    And the region "workspace_browser" status is "ready"
    And the region "current_folder" status is "ready"
    And the region "figures" status is "ready"

  Scenario: Command Window evaluates an expression
    Given a fresh workbench
    When I evaluate "y = 3+4" in the command window
    Then the command window output contains "y ="
    And the workspace contains "y"

  Scenario: Workspace browser lists size and class after eval
    Given a fresh workbench
    When I evaluate "m = [1 2 3]" in the command window
    And I refresh the workspace browser
    Then the workspace browser lists "m" with class "double"

  Scenario: Editor opens and saves a .m file
    Given a fresh workbench
    And a temporary m-file "demo.m" with contents "a = 1;"
    When I open the temporary m-file in the editor
    And I set the editor text to "a = 2;"
    And I save the editor to a new temporary path "demo_out.m"
    Then the temporary file "demo_out.m" contains "a = 2;"
