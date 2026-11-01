Feature: analyst field-assay story (issue #1034, epic #1032)
  @needs_numpy
  Scenario: the washed log keeps the empty West site
    Given a fresh analyst-story session
    When I run the analyst story
    Then "n_clean" is close to [7]
    And "ngroups" is close to [4]
    And "v" is close to [3, 2, 2, 0, 18.4, 21.5, 15.5, nan, 21.2, 18.2, 24.2, nan]
