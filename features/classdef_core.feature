Feature: classdef value classes (Epic #618)
  @needs_numpy
  Scenario: a value class copies on assignment
    Given a class file "PtF" with
      """
      classdef PtF
        properties
          x = 1
        end
        methods
          function obj = setx(obj, v)
            obj.x = v;
          end
        end
      end
      """
    When I evaluate "a = PtF; b = setx(a, 7); r = [a.x b.x];"
    Then variable "r" equals row [1, 7]

  @needs_numpy
  Scenario: a constructor runs with nargin
    Given a class file "CtF" with
      """
      classdef CtF
        properties
          v = 0
        end
        methods
          function obj = CtF(a, b)
            obj.v = nargin;
          end
        end
      end
      """
    When I evaluate "r = [CtF().v CtF(1).v CtF(1, 2).v];"
    Then variable "r" equals row [0, 1, 2]
