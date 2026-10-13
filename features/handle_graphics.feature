Feature: handle graphics (Epic #537)
  @needs_numpy @needs_matplotlib
  Scenario: plot returns a line whose properties can be set
    Given a fresh session
    When I evaluate "p = plot(1:3, [1 4 9]); set(p, 'LineWidth', 2); w = get(p, 'LineWidth');"
    Then variable "w" equals row [2]

  @needs_numpy @needs_matplotlib
  Scenario: hold on accumulates children in one axes
    Given a fresh session
    When I evaluate "plot(1:3); hold on; plot(1:2); n = numel(get(gca, 'Children')); f = numel(get(0, 'Children'));"
    Then variable "n" equals row [2]
    And variable "f" equals row [1]

  @needs_numpy @needs_matplotlib
  Scenario: axis limits
    Given a fresh session
    When I evaluate "plot(1:3); axis([0 4 0 10]); l = [xlim ylim];"
    Then variable "l" equals row [0, 4, 0, 10]
