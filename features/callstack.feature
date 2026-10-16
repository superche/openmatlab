Feature: call stack, MException.stack, getReport and dbstack (Epic #698)
  @needs_numpy
  Scenario: an error in a local function records file lines
    Given a function file "cs1.m" with "function cs1()|  x = 1;|  cs2();|end|function cs2()|  error('c:s', 'oops');|end"
    When I evaluate "try, cs1(); catch e, end; l = [e.stack(1).line e.stack(2).line];"
    Then variable "l" equals row [6, 3]

  @needs_numpy
  Scenario: dbstack reports the caller line
    Given a function file "cs3.m" with "function s = cs3()|  s = cs4();|end|function t = cs4()|  t = dbstack;|end"
    When I evaluate "st = cs3(); l = [st.line];"
    Then variable "l" equals row [5, 2]
