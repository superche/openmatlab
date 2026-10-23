Feature: R-peak findpeaks on one channel (Epic #1010)
  @needs_numpy
  Scenario: the first crest of a 1.2 Hz sine is sample 76
    Given a fresh peak session
    When I evaluate the peaks "n = 600; t = (0:n-1) ./ 360; y = sin(2 .* pi .* 1.2 .* t); [pks, locs] = findpeaks(y, 'MinPeakHeight', 0.5); loc1 = locs(1);"
    Then peak variable "loc1" equals scalar 76

  Scenario: MinPeakDistance keeps the taller of two close spikes
    Given a fresh peak session
    When I evaluate the peaks "y = zeros(1, 20); y(5) = 1; y(8) = 4; y(16) = 2; [pks, locs] = findpeaks(y, 'MinPeakDistance', 5); n = numel(locs);"
    Then peak variable "n" equals scalar 2
