Feature: Workbench workflows (Epic #703)
  @needs_numpy
  Scenario: Run and Advance walks the code sections
    Given a workbench with a three-section script open
    When I press Run and Advance twice
    Then variable "b" in the workbench equals 2
    And the editor caret is on line 5

  @needs_numpy
  Scenario: an error hyperlink opens the file at the error line
    Given a workbench with a three-section script open
    When I run "bad_wf()" in the Command Window
    And I follow the error link
    Then the editor shows "bad_wf.m" at line 3
