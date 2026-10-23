Feature: Record 100 lab-meeting tiledlayout (Epic #1011)
  @needs_numpy
  Scenario: a 2 by 2 layout reports four tiles
    Given a fresh layout session
    When I evaluate the layout "tl = tiledlayout(2, 2); nexttile; plot(1:3); nexttile; plot(1:3); nexttile; histogram(1:4); nexttile; plot(1:3); gs = tl.GridSize; ntiles = numel(tl.Children);"
    Then layout variable "ntiles" equals scalar 4
    And layout variable "gs" equals row [2, 2]
