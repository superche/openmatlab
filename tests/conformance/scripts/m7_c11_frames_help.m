% M7 C11 - caller/base workspace access (evalin/assignin) and help browsing (doc/lookfor/what)
y = 41;
b1 = evalin('base', 'y + 1');
b2 = evalin('caller', 'y * 2');
assignin('base', 'z0', 3);
setter_c11(5);
c1 = xc;
c2 = fromf;
c3 = deep;
c4 = exist('innerset', 'var');
v = reader_c11();
c5 = v;
evalin('base', 'w = 9;');
c6 = w;
r = evalin('base', 'undefined_thing_c11', '-1');
c7 = r;
e1 = 0;
try
  evalin('nowhere', '1');
catch err
  e1 = strcmp(err.identifier, 'MATLAB:evalin:invalidContext');
end
e2 = 0;
try
  assignin('base', '2bad', 1);
catch err
  e2 = strcmp(err.identifier, 'MATLAB:assignin:invalidVariableName');
end
f = @() evalin('caller', 'y');
c8 = f();
d = tempname;
mkdir(d);
fid = fopen(fullfile(d, 'probe_c11.m'), 'w');
fprintf(fid, 'function probe_c11()\n%% PROBE_C11 Zebra keyword for lookfor.\nend\n');
fclose(fid);
addpath(d);
h = help('probe_c11');
c9 = ~isempty(strfind(h, 'PROBE_C11'));
L = lookfor('zebra');
c10 = ~isempty(strfind(L, 'probe_c11'));
s = what(d);
c11 = isstruct(s) && strcmp(s.path, d) && isequal(s.m, {'probe_c11.m'}) && isempty(s.mat);
rmpath(d);
s2 = what('no_such_folder_c11');
c12 = isempty(s2);
t = evalc('doc sin');
c13 = ~isempty(strfind(t, 'sin'));
t2 = evalc('doc');
c14 = ~isempty(strfind(t2, 'help'));

function setter_c11(val)
% SETTER_C11 assigns into the caller and base workspaces.
assignin('caller', 'xc', val);
r = evalin('caller', 'y + 1');
assignin('base', 'fromf', r);
inner_c11();
end

function inner_c11()
assignin('caller', 'innerset', 1);
assignin('base', 'deep', 7);
end

function v = reader_c11()
v = evalin('base', 'z0') + evalin('caller', 'y');
end
