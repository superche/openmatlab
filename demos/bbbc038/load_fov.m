function [I, meta] = load_fov()
%LOAD_FOV  One BBBC038 stage1_test field of view.
%   [I, meta] = load_fov() downloads stage1_test.zip into downloads/bbbc038/
%   when it is not already cached, checks the byte size 9545388, extracts one
%   FOV, and reads it with imread.
%
%   On disk this FOV is 8-bit RGBA. imread returns uint8 RGB in I (256 by 256
%   by 3). The alpha plane is not requested here.
%
%   The zip and the PNG are never committed.
%
%   Licence: CC0 1.0. BBBC038v1, https://bbbc.broadinstitute.org/BBBC038
%   J. C. Caicedo et al., Nature Methods 16:1247-1253, 2019.
%   doi:10.1038/s41592-019-0612-7

meta = bbbc038_fetch();
I = imread(meta.image);
end
