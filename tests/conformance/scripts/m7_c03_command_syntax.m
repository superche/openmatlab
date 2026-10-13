% M7 C03 - command syntax and workspace commands
a = 1; b = 2; c3 = 3;
clear a
ea = exist('a');
eb = exist('b');
clear b c3
eb2 = exist('b');
x1 = 1; x2 = 2; y1 = 3;
clear x*
ex = exist('x1') + exist('x2');
ey = exist('y1');
evv = exist('y1', 'var');
format long
fl = strcmp(strtrim(evalc('disp(pi)')), '3.141592653589793');
format short
fs = strcmp(strtrim(evalc('disp(pi)')), '3.1416');
format
w = who;
nw = iscell(w);
hasy = any(strcmp(w, 'y1'));
s = whos;
ws = isstruct(s) && isfield(s, 'name') && isfield(s, 'class') && isfield(s, 'size');
clear('y1')
ey2 = exist('y1');
old = pwd;
cd ..
up = ~strcmp(pwd, old);
cd(old)
back = strcmp(pwd, old);
L = dir(old);
isd = isstruct(L) && isfield(L, 'name') && isfield(L, 'isdir');
wsin = contains(evalc('which sin'), 'built-in');
wp = ~isempty(which('sin'));
hh = ~isempty(evalc('help sum'));
clc
clc_ok = 1;
dh = strcmp(strtrim(evalc('disp hello')), 'hello');
iv1 = isvarname('a1');
iv2 = isvarname('1a');
hold_free = 1;
