classdef MoneyDemo
  % O-E4 demo: operator, concatenation and disp overloads
  properties
    cents = 0
  end
  methods
    function obj = MoneyDemo(c)
      if nargin, obj.cents = c; end
    end
    function r = plus(a, b)
      r = MoneyDemo(MoneyDemo.raw(a) + MoneyDemo.raw(b));
    end
    function r = mtimes(a, k)
      r = MoneyDemo(MoneyDemo.raw(a) * MoneyDemo.raw(k));
    end
    function t = lt(a, b)
      t = MoneyDemo.raw(a) < MoneyDemo.raw(b);
    end
    function r = horzcat(varargin)
      r = MoneyDemo(sum(cellfun(@MoneyDemo.raw, varargin)));
    end
    function disp(obj)
      fprintf('$%d.%02d\n', fix(obj.cents / 100), mod(obj.cents, 100));
    end
  end
  methods (Static)
    function c = raw(x)
      if isa(x, 'MoneyDemo'), c = x.cents; else, c = x; end
    end
  end
end
