Feature: categorical arrays (Epic #692)
  @needs_numpy
  Scenario: count categories
    Given a fresh session
    When I evaluate "c = categorical({'r','g','r','b'}); n = countcats(c)';"
    Then variable "n" equals row [1, 1, 2]

  @needs_numpy
  Scenario: ordinal comparison
    Given a fresh session
    When I evaluate "o = categorical({'lo','hi','mid'}, {'lo','mid','hi'}, 'Ordinal', true); g = double(o >= 'mid');"
    Then variable "g" equals row [0, 1, 1]

  @needs_numpy
  Scenario: categorical table variable
    Given a fresh session
    When I evaluate "T = table(categorical({'a';'b';'a'}), 'VariableNames', {'g'}); k = sum(T.g == 'a');"
    Then variable "k" equals row [2]
