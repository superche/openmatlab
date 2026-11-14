Feature: ODE solvers, quadrature and optimisation (Epic #627)
  @needs_numpy
  Scenario: ode45 integrates exponential decay at requested times
    When I evaluate "[t, y] = ode45(@(t, y) -y, [0 0.5 1], 1); r = [numel(t) round(1e3 * y(end)) / 1e3];"
    Then variable "r" equals row [3, 0.368]

  @needs_numpy
  Scenario: nonempty Events is an error and does not return a solution
    When I evaluate "try, [t, y] = ode45(@(t, y) error('integrated'), [0 1], 1, odeset('Events', @(t, y) y)); r = [0 0 1]; catch err, r = [1 double(strcmp(err.identifier, 'OpenMATLAB:ode45:UnsupportedOption')) exist('t', 'var')]; end"
    Then variable "r" equals row [1, 1, 0]

  @needs_numpy
  Scenario: quadrature and bounded minimisation
    When I evaluate "r = [quad(@(x) 3*x.^2, 0, 2) integral2(@(x, y) x.*y, 0, 1, 0, 2) round(1e4 * fminbnd(@(x) (x - 2).^2, 0, 5)) / 1e4];"
    Then variable "r" equals row [8, 1, 2]
