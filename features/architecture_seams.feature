# Architecture-stage smoke — not language eval.
Feature: Matrix-first architecture seams
  As a contributor
  I want stable package seams and QA inventories
  So that each R&D iteration stays reviewable and testable

  Scenario: Session composition root exists
    Given a default OpenMATLAB session
    Then the session has a workspace
    And the session function resolver uses the toolbox path

  Scenario: Feature map inventory loads
    When the feature map is loaded
    Then it contains a runtime session feature
    And all feature ids are unique
