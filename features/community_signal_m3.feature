Feature: community.signal hann/kaiser/butter/freqz/filtfilt (Epic #630)
  @needs_numpy
  Scenario: hann and which resolve through the plugin
    When I evaluate "r = [hann(5).' ~isempty(strfind(which('hann'), 'community.signal'))];"
    Then variable "r" equals row [0, 0.5, 1, 0.5, 0, 1]

  @needs_numpy
  Scenario: filtfilt leaves a constant signal unchanged
    When I evaluate "y = filtfilt([0.5 0.5], 1, 5 * ones(1, 7)); r = y;"
    Then variable "r" equals row [5, 5, 5, 5, 5, 5, 5]
