classdef RectDemo < ShapeDemo
  % O-E3 demo: validated properties on a concrete subclass of an abstract base
  properties
    w (1,1) double {mustBePositive} = 1
    h (1,1) double {mustBePositive} = 1
  end
  properties (SetAccess = immutable)
    tag char = 'rect'
  end
  methods
    function obj = RectDemo(w, h)
      if nargin
        obj.w = w;
        obj.h = h;
      end
    end
    function a = area(obj)
      a = obj.w * obj.h;
    end
  end
end
