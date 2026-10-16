Feature: debug engine — breakpoints and stepping (Epic #699)
  @needs_numpy
  Scenario: a breakpoint pauses and dbcont resumes
    Given a function file "bq.m" with "function y = bq(x)|  y = x + 1;|  y = y * 2;|end"
    And the K>> input "y = 10;|dbcont"
    When I evaluate "dbstop in bq at 3; v = bq(1); dbclear all"
    Then variable "v" equals row [20]

  @needs_numpy
  Scenario: dbstatus lists breakpoint lines
    Given a function file "bs.m" with "function bs()|  a = 1;|  b = 2;|end"
    When I evaluate "dbstop in bs at 2; dbstop in bs at 3; s = dbstatus('bs'); l = s.line; dbclear all"
    Then variable "l" equals row [2, 3]
