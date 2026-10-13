% M7 C02 - functions: variadic args, nargin/nargout, local functions, global/persistent, eval/feval
[n, m] = count_args(1, 2, 3);
c = count_args();
v = sum_all(1, 2, 3, 4);
[a, b, c2] = spread([7 8 9]);
no = nout_check();
d = defaults(5);
d2 = defaults(5, 1);
try
  defaults(1, 2, 3);
catch e
  too_many = strcmp(e.identifier, 'MATLAB:TooManyInputs');
end
try
  need_two(1);
catch e
  nchk = strcmp(e.identifier, 'MATLAB:narginchk:notEnoughInputs');
end
k1 = counter();
k2 = counter();
k3 = counter();
global G
G = 5;
g = read_global();
set_global(9);
g2 = G;
eval('ev = 3 + 4;');
eval('bad syntax here (', 'ev_err = 1;');
fv = feval(@plus, 2, 3);
fv2 = feval('max', [4 9 2]);
h = str2func('sum_all');
hv = h(1, 1);
fs = strcmp(func2str(@(x) x + 1), '@(x)x+1');
ex1 = exist('sum');
ex2 = exist('nonexistent_thing_q');
xx = 1;
ex3 = exist('xx');
r = recurse_fact(5);
f2 = @local_twice;
tw = f2(4);
fn_ok = strcmp(func2str(f2), 'local_twice');
ish = isa(f2, 'function_handle');
cf = cellfun(@local_twice, {1, 2});
af = arrayfun(@(t) sum_all(t, t), [1 2 3]);

function [n, m] = count_args(varargin)
  n = nargin;
  m = nargout;
end

function s = sum_all(varargin)
  s = 0;
  for i = 1:numel(varargin)
    s = s + varargin{i};
  end
end

function varargout = spread(v)
  for i = 1:nargout
    varargout{i} = v(i);
  end
end

function r = nout_check()
  r = nargout;
end

function y = defaults(x, inc)
  if nargin < 2
    inc = 10;
  end
  y = x + inc;
end

function need_two(a, b)
  narginchk(2, 2);
end

function k = counter()
  persistent n
  if isempty(n)
    n = 0;
  end
  n = n + 1;
  k = n;
end

function g = read_global()
  global G
  g = G;
end

function set_global(v)
  global G
  G = v;
end

function r = recurse_fact(n)
  if n <= 1
    r = 1;
  else
    r = n * recurse_fact(n - 1);
  end
end

function y = local_twice(x)
  y = 2 * x;
end
