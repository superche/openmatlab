Feature: graphics handle arrays and MATLAB class names (Epic #768, M13 G01)
  @needs_numpy
  Scenario: element property write and cs-list read on a handle array
    When I evaluate "figure('Visible','off'); h = plot(1:3, [1:3; 2:4]'); h(2).LineWidth = 3; r = [h.LineWidth numel(h)]; close all"
    Then variable "r" equals row [0.5, 3, 2]

  @needs_numpy
  Scenario: class names and element-wise validity
    When I evaluate "figure('Visible','off'); h = plot(1:3, [1:3; 2:4]'); c = class(h); delete(h(1)); v = isvalid(h); close all"
    Then variable "c" is the text "matlab.graphics.chart.primitive.Line"
    And variable "v" equals column [0, 1]
