% M13 G05 - colormap / colorbar / clim / image / imagesc / imshow
figure('Visible','off');
c1 = isequal(size(colormap(parula)), [256 3]);
j = jet(64);
c2 = isequal(size(j), [64 3]) && all(j(:) >= 0 & j(:) <= 1);
g = gray(3);
c3 = isequal(g, [0 0 0; 0.5 0.5 0.5; 1 1 1]);
im = imagesc(magic(4));
c4 = strcmp(im.Type, 'image');
cb = colorbar;
c5 = strcmp(class(cb), 'matlab.graphics.illustration.ColorBar');
clim([0 10]);
c6 = isequal(clim, [0 10]);
close all
