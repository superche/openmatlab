classdef LoggedCounterDemo < CounterDemo
  % LoggedCounterDemo  Subclass demo: extends inc via inc@CounterDemo.
  properties
    calls = 0
  end
  methods
    function inc(obj, k)
      if nargin < 2
        k = 1;
      end
      inc@CounterDemo(obj, k);
      obj.calls = obj.calls + 1;
    end
  end
end
