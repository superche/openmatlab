Feature: containers.Map and date/time basics (Epic #539)
  @needs_numpy
  Scenario: a Map is a handle with sorted keys
    Given a fresh session
    When I evaluate "m = containers.Map(); m2 = m; m2('b') = 1; m('a') = 2; n = m.Count;"
    Then variable "n" equals row [2]

  @needs_numpy
  Scenario: datetime arithmetic rolls over months
    Given a fresh session
    When I evaluate "d = datetime(2020, 1, 31) + days(1); p = [month(d) day(d)];"
    Then variable "p" equals row [2, 1]

  @needs_numpy
  Scenario: datenum differences count days
    Given a fresh session
    When I evaluate "n = datenum(2020, 1, 1) - datenum(2019, 1, 1);"
    Then variable "n" equals row [365]
