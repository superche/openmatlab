% M7 C10 - containers.Map and date/time basics
m = containers.Map();
m('a') = 1;
m('b') = [2 3];
k1 = m.Count;
v1 = m('a');
h1 = isKey(m, 'b');
h2 = isKey(m, 'z');
kk = isequal(keys(m), {'a', 'b'});
vs = values(m);
vv = isequal(vs{2}, [2 3]);
remove(m, 'a');
k2 = m.Count;
m2 = containers.Map({'x', 'y'}, {10, 20});
v2 = m2('y');
m3 = containers.Map('KeyType', 'double', 'ValueType', 'any');
m3(3) = 'three';
m3(1) = 'one';
k3 = cell2mat(keys(m3));
mk = 0;
try
  q = m('zz');
catch
  mk = 1;
end
m4 = m;
m4('new') = 5;
hdl = m.Count;
d = datetime(2020, 1, 31);
y = year(d);
mo = month(d);
dd = day(d);
d2 = d + days(1);
d2m = month(d2);
d2d = day(d2);
nd = days(datetime(2020, 3, 1) - datetime(2020, 2, 1));
ds = strcmp(datestr(datenum(2020, 1, 2), 'yyyy-mm-dd'), '2020-01-02');
dn = datenum(2020, 1, 1) - datenum(2019, 1, 1);
dm = minutes(seconds(90));
dcmp = datetime(2021, 1, 1) > datetime(2020, 12, 31);
cv = clock;
cl = numel(cv) == 6 && cv(1) >= 2020;
wd = weekday(datenum(2020, 1, 1));
