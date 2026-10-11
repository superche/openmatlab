Feature: switch case otherwise
  @needs_numpy
  Scenario: first matching case wins
    Given a fresh session
    When I evaluate "x = 2;"
    And I evaluate "switch x\ncase 1\ny = 10;\ncase {2, 3}\ny = 20;\notherwise\ny = 0;\nend"
    Then variable "y" equals 20
