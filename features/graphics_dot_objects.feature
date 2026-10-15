Feature: dot notation on built-in graphics objects (Epic #623)
  @needs_numpy
  Scenario: line and axes properties through h.Prop
    When I evaluate "f = figure('Visible','off'); h = plot(1:3); h.LineWidth = 2; ax = gca; ax.YLim = [0 4]; r = [h.LineWidth ax.YLim get(h,'LineWidth')]; close(f);"
    Then variable "r" equals row [2, 0, 4, 2]

  @needs_numpy
  Scenario: a closed figure invalidates its handles
    When I evaluate "f = figure('Visible','off'); h = plot(1:3); a = isvalid(h); close(f); r = [a isvalid(h) isobject(h)];"
    Then variable "r" equals row [1, 0, 1]
