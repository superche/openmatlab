Feature: Workbench debug UI (Epic #701)
  @needs_numpy
  Scenario: gutter breakpoint pauses a run and Continue finishes it
    Given a workbench with function file "wbb.m"
    When I toggle a breakpoint on line 2 and run "r = wbb(1);"
    Then the debugger is paused at line 2
    When I press Continue
    Then variable "r" in the workbench equals 4

  @needs_numpy
  Scenario: stack selector rebinds the Workspace panel
    Given a workbench with function file "wbb.m"
    When I toggle a breakpoint on line 6 and run "r = wbb(1);"
    And I select stack frame 1
    Then the Workspace panel shows "a"
