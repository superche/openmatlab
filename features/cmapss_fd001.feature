Feature: C-MAPSS FD001 readtable path (Epic #994)
  @needs_numpy
  Scenario: space-delimited file with no header uses PHM08 names
    Given a fresh session
    When I evaluate "f = [tempname '.txt']; fid = fopen(f, 'w'); fprintf(fid, '1  1  0 0 0  1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21\n'); fprintf(fid, '2  4  0 0 0  1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 22\n'); fclose(fid); T = readtable(f, 'Delimiter', ' ', 'ReadVariableNames', false, 'VariableNames', cmapss_names()); h = height(T); w = width(T); s = T.sensor_21'; delete(f);"
    Then variable "h" equals row [2]
    And variable "w" equals row [26]
    And variable "s" equals row [21, 22]
