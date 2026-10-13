% M7 C08 - graphics core: handles, get/set, hold, subplot, decorations, saveas
close all
f = figure;
n0 = get(f, 'Number');
p = plot(1:3, [1 4 9]);
hold on
p2 = plot(1:3, [1 2 3], 'r--');
hold off
ih = ishold;
title('Squares');
xlabel('x');
ylabel('y');
ax = gca;
t_ok = strcmp(get(get(ax, 'Title'), 'String'), 'Squares');
xl_ok = strcmp(get(get(ax, 'XLabel'), 'String'), 'x');
legend('sq', 'lin');
nl = numel(get(ax, 'Children'));
grid on
g_ok = strcmp(get(ax, 'XGrid'), 'on');
axis([0 4 0 10]);
xl = xlim;
yl = ylim;
xlim([1 3]);
xl2 = get(ax, 'XLim');
set(p, 'LineWidth', 2);
lw = get(p, 'LineWidth');
c = get(p2, 'Color');
ls_ok = strcmp(get(p2, 'LineStyle'), '--');
xd = get(p, 'XData');
f2 = figure;
n1 = get(f2, 'Number');
s1 = subplot(2, 1, 1);
plot(1:2);
s2 = subplot(2, 1, 2);
b = bar([3 1 2]);
by = get(b, 'YData');
na = numel(get(f2, 'Children'));
cf = isequal(gcf, f2);
figure(f);
cf2 = isequal(gcf, f);
fn = [tempname '.png'];
saveas(f, fn);
sv = exist(fn, 'file') == 2;
h = histogram([1 2 2 3 3 3], 'BinEdges', [0.5 1.5 2.5 3.5]);
hv = get(h, 'Values');
sc = scatter([1 2], [3 4]);
sx = get(sc, 'XData');
close(f2);
close all
nf = isempty(get(0, 'Children'));
