Feature: events, listeners and objects in MAT files (Epic #624)
  @needs_numpy
  Scenario: notify runs listeners in order with the source
    Given a class file "SigF" with
      """
      classdef SigF < handle
        properties
          hits = []
        end
        events
          Ping
        end
      end
      """
    And a class file "set_hits" with
      """
      function set_hits(src, k)
        src.hits(end+1) = k;
      end
      """
    When I evaluate "s = SigF; addlistener(s, 'Ping', @(src, e) set_hits(src, 1)); addlistener(s, 'Ping', @(src, e) set_hits(src, 2)); notify(s, 'Ping'); r = s.hits;"
    Then variable "r" equals row [1, 2]

  @needs_numpy
  Scenario: a value object survives save and load
    Given a class file "BoxF" with
      """
      classdef BoxF
        properties
          w = 1
        end
      end
      """
    When I evaluate "b = BoxF; b.w = 9; f = [tempname '.mat']; save(f, 'b'); clear b; load(f); r = [b.w isa(b, 'BoxF')];"
    Then variable "r" equals row [9, 1]
