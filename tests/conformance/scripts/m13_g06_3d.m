% M13 G06 - 3-D plotting
figure('Visible','off');
l = plot3(1:3, 1:3, 1:3);
d1 = isequal(l.ZData, 1:3);
[X, Y] = meshgrid(1:3);
s = surf(X, Y, X + Y);
d2 = strcmp(class(s), 'matlab.graphics.chart.primitive.Surface');
m = mesh(X, Y, X .* Y);
d3 = strcmp(m.Type, 'surface');
[~, c] = contour(X, Y, X + Y);
d4 = strcmp(c.Type, 'contour');
view(3);
[az, el] = view;
d5 = az == -37.5 && el == 30;
zlim([0 10]);
d6 = isequal(zlim, [0 10]);
close all
