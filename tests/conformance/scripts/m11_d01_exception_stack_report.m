% M11 D01 - MException.stack (file/name/line) and getReport
d = tempname; mkdir(d);
wf_d01(d, 'f1_d01', { ...
  'function f1_d01()', ...
  '  a = 1;', ...
  '  g_d01(a);', ...
  'end', ...
  'function g_d01(a)', ...
  '  error(''my:id'', ''boom %d'', a + 2);', ...
  'end'});
wf_d01(d, 'Cls_d01', { ...
  'classdef Cls_d01', ...
  '  methods', ...
  '    function bad(obj)', ...
  '      x = 1;', ...
  '      error(''cls:bad'', ''bad method'');', ...
  '    end', ...
  '  end', ...
  'end'});
addpath(d);
try
  f1_d01();
catch e
end
s1 = double(numel(e.stack) >= 2);
s2 = double(contains(e.stack(1).name, 'g_d01'));
s3 = e.stack(1).line;
s4 = double(contains(e.stack(2).name, 'f1_d01'));
s5 = e.stack(2).line;
s6 = double(contains(e.stack(1).file, 'f1_d01.m'));
s7 = isequal(fieldnames(e.stack)', {'file','name','line'});
rb = getReport(e, 'basic');
s8 = double(contains(rb, 'boom 3') && ~contains(rb, 'Error in'));
rx = getReport(e, 'extended', 'hyperlinks', 'off');
s9 = double(contains(rx, 'boom 3') && contains(rx, 'g_d01 (line 6)') && contains(rx, 'f1_d01 (line 3)'));
s10 = double(~contains(rx, '<a href'));
try
  o = Cls_d01();
  o.bad();
catch e2
end
s11 = double(contains(e2.stack(1).name, 'bad'));
s12 = e2.stack(1).line;
m = MException('a:b', 'not thrown');
s13 = size(m.stack);
rmpath(d);

function wf_d01(d, name, lines)
  fid = fopen(fullfile(d, [name '.m']), 'w');
  fprintf(fid, '%s\n', lines{:});
  fclose(fid);
end
