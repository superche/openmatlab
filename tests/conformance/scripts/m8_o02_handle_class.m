% M8 O02 - handle classes: reference semantics, ==, isvalid/delete
% Thick conformance: writes class files into a temp folder on the path.
d = tempname; mkdir(d);
wcls_m8(d, 'CntO2', { ...
  'classdef CntO2 < handle', ...
  '  properties', ...
  '    n = 0', ...
  '  end', ...
  '  methods', ...
  '    function inc(obj, k)', ...
  '      if nargin < 2', ...
  '        k = 1;', ...
  '      end', ...
  '      obj.n = obj.n + k;', ...
  '    end', ...
  '  end', ...
  'end', ...
});
addpath(d);
c = CntO2;
d2 = c;
inc(d2);
c.inc(5);
b1 = c.n;
b2 = d2.n;
b3 = isa(c, 'handle');
b4 = c == d2;
e = CntO2;
b5 = c == e;
b6 = isvalid(c);
delete(e);
b7 = isvalid(e);
b8 = 0;
try
  v = e.n;
catch
  b8 = 1;
end
bump_m8(c);
b9 = c.n;
c.n = 100;
b10 = d2.n;
b11 = isequal(c, d2);
b12 = c ~= e;
rmpath(d);

function wcls_m8(d, name, lines)
  fid = fopen(fullfile(d, [name '.m']), 'w');
  fprintf(fid, '%s\n', lines{:});
  fclose(fid);
end

function bump_m8(h)
  inc(h);
end
