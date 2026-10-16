Feature: datetime arrays and calendar durations (Epic #695)
  @needs_numpy
  Scenario: one month after the 31st of January is the last day of February
    Given a fresh session
    When I evaluate "m = datetime(2020,1,31) + calmonths(1); v = [m.Month m.Day];"
    Then variable "v" equals row [2, 29]

  @needs_numpy
  Scenario: between counts calendar days
    Given a fresh session
    When I evaluate "b = between(datetime(2020,1,15), datetime(2020,3,20), 'days'); v = split(b, 'days');"
    Then variable "v" equals row [65]

  @needs_numpy
  Scenario: setting Month past December rolls into the next year
    Given a fresh session
    When I evaluate "x = datetime(2023,1,1); x.Month = 14; v = [x.Year x.Month];"
    Then variable "v" equals row [2024, 2]

  @needs_numpy
  Scenario: NaT in a datetime array
    Given a fresh session
    When I evaluate "v = double(isnat([datetime(2020,1,1) NaT]));"
    Then variable "v" equals row [0, 1]
