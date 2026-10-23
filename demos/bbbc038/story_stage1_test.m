% BBBC038v1 stage1_test, one FOV (M16 V01-V06).
% Licence: CC0 1.0.
% J. C. Caicedo et al., Nature Methods 16:1247-1253, 2019.
% doi:10.1038/s41592-019-0612-7
% https://bbbc.broadinstitute.org/BBBC038
% stage1_test.zip and the PNG stay in downloads/bbbc038/ and are never committed.
%
% V03 uses global Otsu (graythresh). An RGB image is reduced with the
% published rgb2gray weights 0.2989, 0.5870, 0.1140. Foreground is
% luminance > level. bwareaopen keeps 8-connected components with area >= 50.
% On this FOV those areas are 1, 24, 117, 143, 152, 154, 193, and 219, so 50
% sits between the 24-pixel fragment and the next object.
%
% V04/V05 label that mask with bwlabel and bwconncomp (8-connected).
% regionprops returns Area, Centroid [x y] (column, row, 1-based), and
% Eccentricity from the second central moments. stage1_test has no masks.
% The count is this labeling. Tolerance on the count and the areas is 0.
% The area histogram is its own figure. V06 builds a 2-by-2 lab figure
% (raw FOV, labeloverlay, area histogram, count/mean/median) and a footnote
% for CC0, Caicedo et al. 2019, and BBBC038v1, then closes that figure.
% figure(1) leaves the before/after panel current. The histogram stays the
% only other figure. PNG/PDF export at 300 dpi is I-E5.
%
% From the repository root:
%   openmatlab -e "run('demos/bbbc038/story_stage1_test.m')"

here = fileparts(mfilename('fullpath'));
addpath(here);
[I, meta] = load_fov();
h = size(I, 1);
w = size(I, 2);
c = size(I, 3);
cls = class(I);
nbytes = meta.bytes;
zpath = meta.zip;
ipath = meta.image;
fprintf('BBBC038 V01 zip=%s bytes=%.0f\n', zpath, nbytes);
fprintf('BBBC038 V02 image=%s size=%.0f %.0f %.0f class=%s\n', ipath, h, w, c, cls);
level = graythresh(I);
BW = imbinarize(I);
minarea = 50;
BW2 = bwareaopen(BW, minarea);
nraw = sum(BW(:));
nopen = sum(BW2(:));
bwcls = class(BW2);
fprintf('BBBC038 V03 level=%.10f P=%.0f fg=%.0f open=%.0f class=%s\n', level, minarea, nraw, nopen, bwcls);
tiledlayout(1, 2);
nexttile;
imshow(I);
title('BBBC038 raw');
nexttile;
imshow(BW2);
title('BBBC038 mask');
ntiles = 2;
[L, ncount] = bwlabel(BW2);
CC = bwconncomp(BW2);
stats = regionprops(CC, 'Area', 'Centroid', 'Eccentricity');
ncc = CC.NumObjects;
areas = [stats.Area];
ecc = [stats.Eccentricity];
meanarea = mean(areas);
medarea = median(areas);
meanecc = mean(ecc);
fprintf('BBBC038 V04 count=%.0f objects=%.0f\n', ncount, ncc);
for k = 1:ncount
    fprintf('BBBC038 V04 id=%.0f area=%.0f cx=%.4f cy=%.4f ecc=%.6f\n', ...
        k, stats(k).Area, stats(k).Centroid(1), stats(k).Centroid(2), stats(k).Eccentricity);
end
fprintf('BBBC038 V05 mean=%.4f median=%.4f ecc=%.6f\n', meanarea, medarea, meanecc);
figure;
histogram(areas);
title('BBBC038 areas');
run(fullfile(here, 'lab_figure.m'));
fprintf('BBBC038 V06 grid=%.0f %.0f tiles=%.0f class=%s\n', gs(1), gs(2), labtiles, class(overlay));
fprintf('BBBC038 V06 footnote=%s\n', footnote);
close(fig_lab);
figure(1);
