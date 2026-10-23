Feature: Zero-phase bandpass for one ECG channel (Epic #1009)
  @needs_numpy
  Scenario: filtfilt leaves a constant row unchanged
    Given a fresh filter session
    When I evaluate the filter "y = filtfilt([0.5 0.5], 1, 5 * ones(1, 7));"
    Then filter variable "y" equals row [5, 5, 5, 5, 5, 5, 5]

  Scenario: bandpass matches filtfilt on a passband sine
    Given a fresh filter session
    When I evaluate the filter "fs = 360; t = (0:1439) ./ fs; x = sin(2 .* pi .* 10 .* t); [b, a] = butter(2, [0.5 40] ./ (fs/2), 'bandpass'); y = filtfilt(b, a, x); z = bandpass(x, [0.5 40], fs); d = max(abs(y - z));"
    Then filter variable "d" equals scalar 0
