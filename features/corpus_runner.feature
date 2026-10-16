Feature: Sandboxed corpus runner (Epic #761, M12 C02)
  Scenario: a hanging script times out and the next script still runs
    Given scripts "hang.m" containing "while true, end" and "ok.m" containing "disp(7)"
    When I run them with a 3 second timeout
    Then "hang.m" has status "timeout"
    And "ok.m" has status "pass"

  Scenario: an error keeps its MATLAB identifier
    Given scripts "e.m" containing "error('my:id', 'boom')" and "ok.m" containing "disp(1)"
    When I run them with a 20 second timeout
    Then "e.m" has status "error"
    And "e.m" has error id "my:id"
