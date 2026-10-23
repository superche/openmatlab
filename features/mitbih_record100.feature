Feature: MIT-BIH record 100 format 212 load (Epic #1008)
  @needs_numpy
  Scenario: gain and baseline convert the first frame to millivolts
    Given a two-sample format 212 record
    When I evaluate "R = mitbih_load(fix); fs = R.fs; n = size(R.sig, 1); c = size(R.sig, 2); s = R.sig(1, :);"
    Then variable "fs" equals row [360]
    And variable "n" equals row [2]
    And variable "c" equals row [2]
    And variable "s" equals row [-0.145, -0.065]
