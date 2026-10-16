% M13 G02 - findobj / findall / allchild / gco / ancestor / axes / groot
f = figure('Visible','off');
ax = axes(f);
hold(ax, 'on');
l1 = plot(ax, 1:3, 'Tag', 'a');
l2 = plot(ax, 3:-1:1, 'Tag', 'b', 'Color', 'r');
q1 = numel(findobj(f, 'Type', 'line'));
q2 = isequal(findobj(f, 'Tag', 'b'), l2);
q3 = isequal(findobj(f, '-regexp', 'Tag', '^a$'), l1);
q4 = numel(findobj(f, 'Type', 'line', '-and', '-not', 'Tag', 'a')) == 1;
q5 = isequal(ancestor(l1, 'figure'), f);
c = allchild(ax);
q6 = isequal(c(1), l2);
q7 = isequal(groot, groot) && strcmp(get(groot, 'Type'), 'root');
q8 = numel(findall(f, 'Type', 'axes')) == 1;
close all
