Feature: property validation and abstract classes (Epic #620)
  @needs_numpy
  Scenario: a validated property converts, reshapes and rejects
    Given a class file "ValF" with
      """
      classdef ValF
        properties
          w (1,:) double {mustBeNonnegative} = [0 0]
        end
      end
      """
    When I evaluate "o = ValF; o.w = [1; 2]; try, o.w = -1; e = 0; catch, e = 1; end; r = [size(o.w) e];"
    Then variable "r" equals row [1, 2, 1]

  @needs_numpy
  Scenario: an abstract base cannot be instantiated but a concrete subclass can
    Given a class file "ShapeF" with
      """
      classdef (Abstract) ShapeF
        methods (Abstract)
          a = area(obj)
        end
      end
      """
    And a class file "UnitF" with
      """
      classdef UnitF < ShapeF
        methods
          function a = area(obj)
            a = 1;
          end
        end
      end
      """
    When I evaluate "try, s = ShapeF; e = 0; catch, e = 1; end; r = [e area(UnitF)];"
    Then variable "r" equals row [1, 1]
