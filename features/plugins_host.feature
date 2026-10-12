Feature: VS Code-style plugin host
  As a community plugin author
  I want a published host contract
  So I can contribute commands and path entries without forking the shell

  Scenario: Sample community plugin activates and runs a command
    Given the community.signal sample plugin is discovered
    When the plugin host activates on startup
    And I execute the command "community.signal.demo"
    Then the command result contains "demo OK"
    And the plugin state is "active"

  Scenario: Community signal demo calls clean-room hamming
    Given the community.signal sample plugin is discovered
    When the plugin host activates on startup
    And I execute the command "community.signal.demo"
    Then the command result contains "hamming(5)="
    And the plugin state is "active"
