Feature: Workbench output routing to the Command Window (Epic #767, #760)
  Scenario: a script's fprintf and disp output appears in the Command Window
    Given a workbench with a script "s.m" containing "fprintf('total = %d\n', 7); disp('hello')"
    When I run "s.m" from the editor
    Then the Command Window shows "total = 7"
    And the Command Window shows "hello"

  Scenario: a warning appears in the Command Window
    Given a workbench with a script "w.m" containing "warning('w:x', 'careful');"
    When I run "w.m" from the editor
    Then the Command Window shows "Warning: careful"
