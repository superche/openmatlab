Feature: errors and exceptions (Epic #530)
  @needs_numpy
  Scenario: try/catch binds an MException with id and formatted message
    Given a fresh session
    When I evaluate "try, error('my:id', 'v=%d', 7); catch e, a = strcmp(e.identifier, 'my:id'); b = strcmp(e.message, 'v=7'); c = strcmp(class(e), 'MException'); end"
    Then variable "a" equals row [1]
    And variable "b" equals row [1]
    And variable "c" equals row [1]

  @needs_numpy
  Scenario: builtin errors carry MATLAB identifiers
    Given a fresh session
    When I evaluate "x = [1 2]; try, x(5); catch e, a = strcmp(e.identifier, 'MATLAB:badsubscript'); end"
    Then variable "a" equals row [1]

  @needs_numpy
  Scenario: rethrow and throw propagate to an outer handler
    Given a fresh session
    When I evaluate "try, try, throw(MException('p:q', 'in')); catch e, rethrow(e); end; catch o, a = strcmp(o.identifier, 'p:q'); end"
    Then variable "a" equals row [1]

  @needs_numpy
  Scenario: break inside try leaves the loop and is not caught
    Given a fresh session
    When I evaluate "n = 0; for i = 1:5, try, n = n + 1; if i == 2, break; end; catch, n = 100; end; end"
    Then variable "n" equals row [2]

  @needs_numpy
  Scenario: assert and lasterr
    Given a fresh session
    When I evaluate "try, assert(1 == 2, 'bad %d', 3); catch e, a = strcmp(e.message, 'bad 3'); end; b = strcmp(lasterr, 'bad 3');"
    Then variable "a" equals row [1]
    And variable "b" equals row [1]
