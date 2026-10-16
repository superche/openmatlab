% M13 G08 - savefig / openfig / exportgraphics / print
d = tempname; mkdir(d);
f = figure('Visible','off');
plot(1:3, 'LineWidth', 2, 'Tag', 'k');
title('T');
savefig(f, fullfile(d, 'a.fig'));
close(f);
g = openfig(fullfile(d, 'a.fig'), 'invisible');
l = findobj(g, 'Tag', 'k');
s1 = numel(l) == 1 && l.LineWidth == 2;
s2 = strcmp(get(get(gca, 'Title'), 'String'), 'T');
exportgraphics(g, fullfile(d, 'a.png'), 'Resolution', 72);
s3 = isfile(fullfile(d, 'a.png'));
print(g, fullfile(d, 'b'), '-dpdf');
s4 = isfile(fullfile(d, 'b.pdf'));
saveas(g, fullfile(d, 'c.fig'));
s5 = isfile(fullfile(d, 'c.fig'));
close all
rmdir(d, 's');
