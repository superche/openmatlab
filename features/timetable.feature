Feature: timetable (Epic #697)
  @needs_numpy
  Scenario: select rows by a time range
    Given the MATLAB code "t = datetime(2020,1,1) + hours(0:5)'; x = (1:6)'; TT = timetable(t, x); S = TT(timerange(datetime(2020,1,1,1,0,0), datetime(2020,1,1,3,0,0)), :); v = S.x';"
    Then v equals "2 3"

  @needs_numpy
  Scenario: retime to a regular two-hour mean
    Given the MATLAB code "t = datetime(2020,1,1) + hours(0:5)'; x = (1:6)'; TT = timetable(t, x); R = retime(TT, 'regular', 'mean', 'TimeStep', hours(2)); v = R.x';"
    Then v equals "1.5 3.5 5.5"
