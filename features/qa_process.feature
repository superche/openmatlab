Feature: QA process inventories
  As a maintainer
  I want off-the-shelf Issues and Gherkin-backed checks
  So that work and verification stay separate but linked

  Scenario: Test catalog lists active unit cases
    When the test catalog is loaded
    Then there is at least one active unit test case
