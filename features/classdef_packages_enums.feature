Feature: packages, import, enumerations and introspection (Epic #622)
  @needs_numpy
  Scenario: package function called by full name and after import
    Given a class file "+pk/sq" with
      """
      function y = sq(x)
        y = x.^2;
      end
      """
    When I evaluate "a = pk.sq(3); import pk.*; b = sq(4); r = [a b];"
    Then variable "r" equals row [9, 16]

  @needs_numpy
  Scenario: integer-based enumeration members compare and convert
    Given a class file "LvF" with
      """
      classdef LvF < int32
        enumeration
          Low (1)
          High (10)
        end
      end
      """
    When I evaluate "r = [double(LvF.High) LvF.High > LvF.Low numel([LvF.Low LvF.High])];"
    Then variable "r" equals row [10, 1, 2]

  @needs_numpy
  Scenario: enumeration members drive switch
    Given a class file "ColF" with
      """
      classdef ColF
        enumeration
          Red, Green
        end
      end
      """
    When I evaluate "c = ColF.Green; switch c, case ColF.Red, k = 1; case ColF.Green, k = 2; end; r = [k isenum(c)];"
    Then variable "r" equals row [2, 1]
