Feature: 2-D chart breadth and annotations (Epic #772, M13 G04/G07)
  @needs_numpy
  Scenario: chart objects carry MATLAB types
    When I evaluate "figure('Visible','off'); e = errorbar(1:3, [2 3 4], [1 1 1]); c = class(e); close all"
    Then variable "c" is the text "matlab.graphics.chart.primitive.ErrorBar"

  @needs_numpy
  Scenario: stacked bars return one handle per column
    When I evaluate "figure('Visible','off'); b = bar([1 2; 3 4], 'stacked'); r = [numel(b) numel(pie([1 2]))]; close all"
    Then variable "r" equals row [2, 4]
