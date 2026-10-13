classdef CounterDemo < handle
  % CounterDemo  Handle-class demo: every copy is the same object.
  properties
    n = 0
  end
  methods
    function inc(obj, k)
      if nargin < 2
        k = 1;
      end
      obj.n = obj.n + k;
    end
  end
end
