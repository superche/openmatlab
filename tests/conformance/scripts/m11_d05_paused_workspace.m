% M11 D05 - paused-frame evaluation, dbup/dbdown, who, evalin, assignment on resume
% Paused-session commands come from m11_d05_paused_workspace.queue.
d = tempname; mkdir(d);
wf_d05(d, 'pw_d05', { ...
  'function r = pw_d05(a)', ...
  '  b = a * 2;', ...
  '  r = inner_d05(b);', ...
  'end', ...
  'function q = inner_d05(c)', ...
  '  q = c + 1;', ...
  'end'});
addpath(d);
global G_D05
G_D05 = [];
dbstop in pw_d05 at 6
r = pw_d05(5);
dbclear all
w1 = G_D05;
w2 = r;
rmpath(d);

function wf_d05(d, name, lines)
  fid = fopen(fullfile(d, [name '.m']), 'w');
  fprintf(fid, '%s\n', lines{:});
  fclose(fid);
end
