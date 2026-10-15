Feature: Functions residual from #569 (Issue #640)
  @needs_numpy
  Scenario: addSwitch toggles a logical Results field
    Given a fresh session
    When I evaluate "p = inputParser; addSwitch(p, 'Verbose'); parse(p, 'Verbose'); on = p.Results.Verbose; parse(p); off = p.Results.Verbose; r = [double(on) double(off)];"
    Then variable "r" equals row [1, 0]

  @needs_numpy
  Scenario: PartialMatching false rejects unique prefixes
    Given a fresh session
    When I evaluate "p = inputParser; addParameter(p, 'Mode', 'fast'); p.PartialMatching = false; try, parse(p, 'Mo', 'x'); e = 0; catch, e = 1; end"
    Then variable "e" equals row [1]
