% M11 D07 - dbstop if caught error [ID] / warning / naninf
% Paused-session commands come from m11_d07_error_stop.queue.
d = tempname; mkdir(d);
wf_d07(d, 'ef_d07', { ...
  'function r = ef_d07(x)', ...
  '  r = x + 1;', ...
  '  error(''d07:bad'', ''bad'');', ...
  'end'});
wf_d07(d, 'wf2_d07', { ...
  'function wf2_d07()', ...
  '  warning(''d07:w'', ''careful'');', ...
  'end'});
wf_d07(d, 'nf_d07', { ...
  'function nf_d07()', ...
  '  z = 1 / 0;', ...
  'end'});
addpath(d);
global E_D07
E_D07 = [];
dbstop if caught error d07:bad
try
  ef_d07(1);
catch me
end
e1 = double(strcmp(me.identifier, 'd07:bad'));
dbclear all
dbstop if caught error other:id
try
  ef_d07(1);
catch
end
e2 = numel(E_D07);
dbclear all
dbstop if warning
wf2_d07();
dbclear all
dbstop if naninf
nf_d07();
dbclear all
e3 = E_D07;
e4 = isempty(dbstatus);
rmpath(d);

function wf_d07(d, name, lines)
  fid = fopen(fullfile(d, [name '.m']), 'w');
  fprintf(fid, '%s\n', lines{:});
  fclose(fid);
end
