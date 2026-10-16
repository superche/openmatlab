% M13 G03 - tiledlayout / nexttile / yyaxis / nice ticks / axis modes
figure('Visible','off');
t = tiledlayout(2, 2);
a1 = strcmp(class(t), 'matlab.graphics.layout.TiledChartLayout');
ax1 = nexttile;
plot(ax1, [0.3 9.7]);
yl = ylim(ax1);
a2 = yl(1) <= 0.3 && yl(2) >= 9.7 && yl(1) == round(yl(1)) && yl(2) == round(yl(2));
ax2 = nexttile([1 2]);
a3 = isgraphics(ax2, 'axes');
yyaxis(ax2, 'right');
plot(ax2, 1:3);
a4 = strcmp(ax2.YAxisLocation, 'right');
axis(ax1, 'equal');
a5 = strcmp(ax1.DataAspectRatioMode, 'manual');
axis(ax1, 'ij');
a6 = strcmp(ax1.YDir, 'reverse');
close all
