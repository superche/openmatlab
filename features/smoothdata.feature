Feature: smoothdata for the FD001 story (Epic #995)
  @needs_numpy
  Scenario: movmean method matches movmean on a window
    When I evaluate "a = smoothdata(1:6, 'movmean', 4); b = movmean(1:6, 4); d = max(abs(a - b)); c = smoothdata([1 2 3 4 5], 'movmean', [1 0]); e = movmean([1 2 3 4 5], [1 0]); f = max(abs(c - e));"
    Then variable "a" equals row [1.5, 2, 2.5, 3.5, 4.5, 5]
    And variable "d" equals row [0]
    And variable "f" equals row [0]

  @needs_numpy
  Scenario: gaussian keeps a constant and damps a spike as the window grows
    When I evaluate "k = smoothdata([5 5 5 5], 'gaussian', 3); x = [0 0 0 10 0 0 0]; g3 = smoothdata(x, 'gaussian', 3); g7 = smoothdata(x, 'gaussian', 7); ok = all(k == 5) && g3(4) < 10 && g3(4) > g7(4) && g7(4) > 0;"
    Then variable "ok" equals row [1]
