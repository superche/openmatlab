% M13 G01 - graphics handle arrays, class names, display
figure('Visible','off');
h = plot(1:3, [1:3; 2:4; 3:5]');
h1 = strcmp(class(h), 'matlab.graphics.chart.primitive.Line');
h(2).LineWidth = 3;
h2 = h(2).LineWidth == 3;
h3 = h(2).LineWidth;
w = get(h, 'LineWidth');
h4 = iscell(w) && numel(w) == 3;
lw = [h.LineWidth];
h5 = isequal(size(lw), [1 3]);
out = evalc('disp(h(1))');
h6 = contains(out, 'Line with properties');
h7 = reshape(isgraphics(h), 1, []);
h8 = isa(double(h(1)), 'double');
ax = gca;
h9 = strcmp(class(ax), 'matlab.graphics.axis.Axes');
delete(h);
h10 = reshape(isvalid(h), 1, []);
close all
