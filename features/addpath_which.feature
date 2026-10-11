Feature: Language addpath and which
  As a user
  I want addpath/which in the language
  So I can load .m functions from the REPL without Python APIs

  @needs_numpy
  Scenario: addpath then call
    Given a temp toolbox with "add2"
    When I evaluate addpath to that toolbox
    And I evaluate "r = add2(2, 3);"
    Then variable "r" equals 5
