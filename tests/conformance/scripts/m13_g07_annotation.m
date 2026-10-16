% M13 G07 - text / annotation / legend
figure('Visible','off');
plot(1:3, 'DisplayName', 'alpha');
t = text(1, 2, 3, 'x^2', 'Interpreter', 'none');
n1 = numel(t.Position) == 3 && strcmp(t.Interpreter, 'none');
an = annotation('arrow', [0.1 0.2], [0.1 0.2]);
n2 = strcmp(an.Type, 'arrowshape');
tb = annotation('textbox', [0.1 0.1 0.2 0.2], 'String', 'hi');
n3 = strcmp(tb.Type, 'textboxshape');
lg = legend('Location', 'northwest');
n4 = strcmp(lg.String{1}, 'alpha') && strcmp(lg.Location, 'northwest');
legend('off');
n5 = isempty(findobj(gcf, 'Type', 'legend'));
close all
