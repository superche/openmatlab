% M7 C01 - errors and exceptions (public MATLAB docs: try/catch, error, MException)
r1 = 0;
try
  error('boom');
catch
  r1 = 1;
end
try
  error('my:id', 'value %d too big', 7);
catch e
  id_ok = strcmp(e.identifier, 'my:id');
  msg_ok = strcmp(e.message, 'value 7 too big');
end
try
  x = [1 2 3];
  y = x(5);
catch e2
  oob_id = strcmp(e2.identifier, 'MATLAB:badsubscript');
end
ME = MException('pkg:fn', 'bad %s', 'input');
try
  throw(ME);
catch e3
  me_ok = strcmp(e3.message, 'bad input') && strcmp(e3.identifier, 'pkg:fn');
  cls = strcmp(class(e3), 'MException');
end
try
  try
    error('inner:x', 'inner');
  catch e4
    rethrow(e4);
  end
catch e5
  re_ok = strcmp(e5.identifier, 'inner:x');
end
try
  assert(1 == 2, 'check failed %d', 3);
catch e6
  as_ok = strcmp(e6.message, 'check failed 3');
end
assert(true);
fin = 0;
for k = 1:3
  try
    if k == 2
      error('skip');
    end
    fin = fin + k;
  catch
    fin = fin + 10;
  end
end
s = struct('message', 'from struct', 'identifier', 's:t');
try
  error(s);
catch e7
  st_ok = strcmp(e7.identifier, 's:t') && strcmp(e7.message, 'from struct');
end
le_ok = strcmp(lasterr, 'from struct');
try
  undefined_fn_xyz(1);
catch e8
  undef_id = strcmp(e8.identifier, 'MATLAB:UndefinedFunction');
end
try
  error('pct:x', 'pct: %d%%', 50);
catch e9
  pct_ok = strcmp(e9.message, 'pct: 50%');
end
try
  error('literal 100%');
catch e10
  lit_ok = strcmp(e10.message, 'literal 100%');
end
try
  error('a:b', 'line\nbreak');
catch e11
  esc_ok = numel(e11.message) == 10;
end
w = 0;
while true
  try
    w = w + 1;
    if w > 2
      error('stop:loop', 'stop');
    end
  catch
    break
  end
end
