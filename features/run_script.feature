Feature: run script
  As a user
  I want run("file.m")
  So scripts on disk initialize my session

  @needs_numpy
  Scenario: run sets workspace vars
    Given a session with script file on disk
    When I run that script via language run
    Then variable "k" equals 9
