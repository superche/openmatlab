Feature: Variable editor (Epic #702)
  @needs_numpy
  Scenario: edit a matrix cell and it writes back
    Given a workbench where "A = [1 2; 3 4];" has run
    When I open "A" in the variable editor and set cell 2,1 to "30"
    Then the workbench value of "A(2,1)" is 30

  @needs_numpy
  Scenario: a bad edit is rejected and leaves the variable unchanged
    Given a workbench where "A = [1 2; 3 4];" has run
    When I open "A" in the variable editor and set cell 1,1 to "1+"
    Then the variable editor reports an error
    And the workbench value of "A(1,1)" is 1
