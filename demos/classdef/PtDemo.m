classdef PtDemo
  % PtDemo  Value-class demo for the M8 acceptance packages.
  properties
    x = 0
    y = 0
  end
  properties (Dependent)
    r
  end
  methods
    function obj = PtDemo(x, y)
      if nargin > 0
        obj.x = x;
        obj.y = y;
      end
    end
    function obj = shift(obj, dx)
      obj.x = obj.x + dx;
    end
    function v = get.r(obj)
      v = hypot(obj.x, obj.y);
    end
  end
end
