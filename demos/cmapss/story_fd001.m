% NASA C-MAPSS FD001 story stub (M14 V01, V02).
% Saxena, Goebel, Simon, and Eklund, PHM08.
% Data: DOI 10.5281/zenodo.15346912 (CC BY 4.0).
% The zip and the text files stay in downloads/cmapss/ and are never committed.
%
% From the repository root:
%   openmatlab -e "run('demos/cmapss/story_fd001.m')"

here = fileparts(mfilename('fullpath'));
addpath(here);
T = load_fd001('train');
h = height(T);
w = width(T);
u = numel(unique(T.unit));
n1 = sum(T.unit == 1);
fprintf('FD001 train height=%g width=%g unique_units=%g unit1_cycles=%g\n', h, w, u, n1);
