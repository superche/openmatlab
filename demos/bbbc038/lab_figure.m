% V06 lab-meeting figure for one BBBC038 FOV (M16 I-E4).
% Caller workspace: I, L, areas, ncount, meanarea, medarea.
% The story closes fig_lab afterwards. The 1-by-2 before/after panel and the
% standalone area histogram stay the figures the V03 and V04 checks see.
% Licence: CC0 1.0. Caicedo et al., Nature Methods 2019. BBBC038v1.

overlay = labeloverlay(I, L);
footnote = 'CC0 1.0. J. C. Caicedo et al., Nature Methods 16:1247-1253, 2019. BBBC038v1.';
summary = sprintf('Nuclei %.0f\nMean area %.0f px\nMedian area %.0f px', ncount, meanarea, medarea);
fig_lab = figure('Position', [100 100 1200 900]);
tl = tiledlayout(2, 2, 'TileSpacing', 'compact', 'Padding', 'loose');
tl.Title.String = 'BBBC038v1 stage1_test';
tl.XLabel.String = footnote;
nexttile;
imshow(I);
title('BBBC038 raw');
nexttile;
imshow(overlay);
title('BBBC038 overlay');
nexttile;
histogram(areas);
title('Area (px)');
xlabel('Area (px)');
ylabel('Count');
nexttile;
axis off;
text(0.05, 0.72, summary);
title('BBBC038 summary');
gs = tl.GridSize;
labtiles = numel(tl.Children);
