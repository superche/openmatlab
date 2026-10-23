Feature: heatmap for a matrix (Epic #997)
  A correlation matrix is drawn with category labels and a colorbar.
  The color scale is the one the call asked for.

  @needs_numpy
  Scenario: labels and color limits are stored on the chart
    When I evaluate "h = heatmap({'a','b'}, {'u','v'}, [1 0; 0 1], 'ColorLimits', [-1 1]); cls = class(h); vis = h.ColorbarVisible; cd = h.ColorData; clim = h.ColorLimits; xl = h.XDisplayLabels;"
    Then variable "cls" equals text "matlab.graphics.chart.HeatmapChart"
    And variable "vis" equals text "on"
    And variable "cd" equals matrix [1 0; 0 1]
    And variable "clim" equals row [-1, 1]
    And variable "xl" equals text row [a, b]
