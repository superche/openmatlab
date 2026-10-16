% M11 D03 - dbstop/dbclear/dbstatus, conditional breakpoints, pause when hit
% Paused-session commands come from m11_d03_breakpoints.queue (fed to the K>> prompt).
d = tempname; mkdir(d);
wf_d03(d, 'bp_d03', { ...
  'function y = bp_d03(x)', ...
  '  y = x + 1;', ...
  '  y = y * 2;', ...
  'end'});
addpath(d);
dbstop in bp_d03 at 3
s = dbstatus('bp_d03');
k1 = numel(s);
k2 = s(1).line;
dbstop in bp_d03 at 2
s = dbstatus('bp_d03');
k3 = sort(s(1).line);
dbclear in bp_d03 at 2
s = dbstatus('bp_d03');
k4 = s(1).line;
dbclear all
k5 = isempty(dbstatus);
dbstop in bp_d03
s = dbstatus('bp_d03');
k6 = s(1).line;
dbclear all
dbstop in bp_d03 at 3 if x > 5
s = dbstatus('bp_d03');
k7 = double(contains(s(1).expression{1}, 'x > 5'));
global HIT_D03
HIT_D03 = [];
y1 = bp_d03(1);
y2 = bp_d03(10);
k8 = HIT_D03;
k9 = [y1 y2];
dbclear all
k10 = isempty(dbstatus);
rmpath(d);

function wf_d03(d, name, lines)
  fid = fopen(fullfile(d, [name '.m']), 'w');
  fprintf(fid, '%s\n', lines{:});
  fclose(fid);
end
