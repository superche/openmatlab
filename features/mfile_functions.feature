Feature: Path .m functions
  As a user
  I want functions on ToolboxPath to be callable
  So that I can reuse algorithms as .m files

  @needs_numpy
  Scenario: Call add2 from path
    Given a session with path fixture "add2"
    When I evaluate "r = add2(10, 5);"
    Then variable "r" equals 15
