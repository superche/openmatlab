Feature: Corpus report, regression gate and corpus issue filing (Epic #764, M12 C10)
  Scenario: a pass that turns into a failure fails the gate
    Given a baseline where entry "b" passes
    When a new run reports "b" as an error
    Then the gate lists "b" as a regression

  Scenario: the same root cause is filed once
    Given two failures with category "missing-builtin" and key "strmatch"
    When I group the failures
    Then there is one group of 2 entries
    And filing twice opens only one issue
