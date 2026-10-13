Feature: handle classes and inheritance (Epic #619)
  @needs_numpy
  Scenario: a handle is shared between variables
    Given a class file "CntF" with
      """
      classdef CntF < handle
        properties
          n = 0
        end
        methods
          function inc(obj)
            obj.n = obj.n + 1;
          end
        end
      end
      """
    When I evaluate "a = CntF; b = a; inc(b); b.inc(); r = [a.n (a == b)];"
    Then variable "r" equals row [2, 1]

  @needs_numpy
  Scenario: a subclass calls its superclass method
    Given a class file "BaseF" with
      """
      classdef BaseF
        methods
          function v = val(obj)
            v = 1;
          end
        end
      end
      """
    And a class file "SubF" with
      """
      classdef SubF < BaseF
        methods
          function v = val(obj)
            v = 10 + val@BaseF(obj);
          end
        end
      end
      """
    When I evaluate "r = [val(SubF()) isa(SubF(), 'BaseF')];"
    Then variable "r" equals row [11, 1]
