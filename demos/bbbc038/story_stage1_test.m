% BBBC038v1 stage1_test, one FOV (M16 V01-V02).
% Licence: CC0 1.0.
% J. C. Caicedo et al., Nature Methods 16:1247-1253, 2019.
% doi:10.1038/s41592-019-0612-7
% https://bbbc.broadinstitute.org/BBBC038
% stage1_test.zip and the PNG stay in downloads/bbbc038/ and are never committed.
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
