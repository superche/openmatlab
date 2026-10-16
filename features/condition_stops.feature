Feature: keyboard, input and condition stops (Epic #700)
  @needs_numpy
  Scenario: input evaluates the reply
    Given a fresh session with input lines "3+4"
    When I evaluate "x = input('Enter: ');"
    Then variable "x" equals row [7]

  @needs_numpy
  Scenario: dbstop if naninf pauses at the faulting line
    Given a fresh session with input lines "s_ = dbstack; L = s_(1).line; assignin('base', 'L', L);|dbcont"
    When I evaluate "f = [tempname '.m']; [p, n] = fileparts(f); fid = fopen(f, 'w'); fprintf(fid, 'function %s()\n  q = 1;\n  z = 1 / 0;\nend\n', n); fclose(fid); addpath(p); dbstop if naninf; feval(n); dbclear all;"
    Then variable "L" equals row [3]
