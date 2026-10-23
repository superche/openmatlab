function T = load_fd001(which)
%LOAD_FD001  Read NASA C-MAPSS FD001 the way a MATLAB script would.
%   T = load_fd001() loads train_FD001.txt.
%   T = load_fd001('train') or load_fd001('test') is a 26-column table.
%   T = load_fd001('rul') is the test-set remaining-useful-life column.
%
%   Names follow the PHM08 readme: unit number, time in cycles, three
%   operational settings, and 21 sensor measurements. The upstream readme
%   labels column 26 "sensor measurement 26"; that column is sensor 21.
%
%   cmapss_fetch downloads the zip at runtime into downloads/cmapss/.
%   The zip and the text files are never committed.
%
%   Citation: A. Saxena, K. Goebel, D. Simon, and N. Eklund, "Damage
%   Propagation Modeling for Aircraft Engine Run-to-Failure Simulation",
%   PHM08, 2008. Data: DOI 10.5281/zenodo.15346912 (CC BY 4.0).

if nargin < 1
    which = 'train';
end
if strcmp(which, 'train')
    file = 'train_FD001.txt';
    wide = 1;
elseif strcmp(which, 'test')
    file = 'test_FD001.txt';
    wide = 1;
elseif strcmp(which, 'rul')
    file = 'RUL_FD001.txt';
    wide = 0;
else
    error('OpenMATLAB:cmapss:BadSplit', 'load_fd001: which must be train, test, or rul.');
end
root = cmapss_fetch();
if wide
    names = cmapss_names();
else
    names = {'rul'};
end
T = readtable(fullfile(root, file), 'Delimiter', ' ', 'ReadVariableNames', false, 'VariableNames', names);
end
