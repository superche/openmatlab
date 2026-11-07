Feature: calendar-width group bins (issue #1070)
  @needs_numpy
  Scenario: a calendar year is one bin and January 1 starts the next year
    Given a fresh analyst session
    When I run "t = datetime([2016 12 31; 2017 1 1; 2017 6 1]); x = [1; 10; 4]; T = table(t, x); S = groupsummary(T, 't', 'year', 'sum', 'x'); v = S.sum_x';"
    Then "v" is close to [1, 14]

  @needs_numpy
  Scenario: datetime edges close the last bin
    Given a fresh analyst session
    When I run "edges = [datetime(2017,1,1) datetime(2017,6,1) datetime(2018,1,1)]; t = [datetime(2017,1,15); datetime(2017,5,31); datetime(2017,6,1); datetime(2018,1,1)]; x = [1; 2; 4; 8]; T = table(t, x); S = groupsummary(T, 't', edges, 'sum', 'x'); v = S.sum_x';"
    Then "v" is close to [3, 12]

  @needs_numpy
  Scenario: groupcounts uses the same year bins
    Given a fresh analyst session
    When I run "t = datetime([2016 1 1; 2016 6 1; 2017 1 1]); T = table(t); C = groupcounts(T, 't', 'year'); v = C.GroupCount';"
    Then "v" is close to [2, 1]
