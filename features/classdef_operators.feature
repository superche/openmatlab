Feature: operator and indexing overloads (Epic #621)
  @needs_numpy
  Scenario: plus is overloaded for either operand order
    Given a class file "AddF" with
      """
      classdef AddF
        properties
          v = 0
        end
        methods
          function obj = AddF(v)
            obj.v = v;
          end
          function r = plus(a, b)
            if isa(a, 'AddF'), a = a.v; end
            if isa(b, 'AddF'), b = b.v; end
            r = AddF(a + b);
          end
        end
      end
      """
    When I evaluate "x = AddF(2) + 3; y = 4 + AddF(1); r = [x.v y.v];"
    Then variable "r" equals row [5, 5]

  @needs_numpy
  Scenario: subsref overload with builtin fallback
    Given a class file "TenF" with
      """
      classdef TenF
        properties
          d = [1 2 3]
        end
        methods
          function v = subsref(obj, s)
            if strcmp(s(1).type, '()')
              v = obj.d(s(1).subs{:}) * 10;
            else
              v = builtin('subsref', obj, s);
            end
          end
        end
      end
      """
    When I evaluate "t = TenF; r = [t(2) t.d(3)];"
    Then variable "r" equals row [20, 3]
