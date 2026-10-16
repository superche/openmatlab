% M13 G04 - 2-D chart breadth
figure('Visible','off');
e = errorbar(1:3, [2 3 4], [0.1 0.2 0.3]);
b1 = strcmp(class(e), 'matlab.graphics.chart.primitive.ErrorBar');
a = area(1:3, [1 2 3]);
b2 = strcmp(a.Type, 'area');
s = stairs(1:3);
b3 = strcmp(s.Type, 'stair');
st = stem(1:3);
b4 = strcmp(st.Type, 'stem');
p = pie([1 2 3]);
b5 = numel(p) == 6;
bh = barh([1 2; 3 4], 'stacked');
b6 = numel(bh) == 2;
h = histogram([1 2 2 3 3 3], 'BinEdges', 0.5:1:3.5);
b7 = isequal(h.Values, [1 2 3]);
pa = patch([0 1 1], [0 0 1], 'r');
b8 = strcmp(pa.Type, 'patch');
close all
