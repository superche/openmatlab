Feature: formatted and file I/O, save/load (Epic #533)
  @needs_numpy
  Scenario: fprintf to a file and read it back
    Given a fresh session
    When I evaluate "f = [tempname '.txt']; fid = fopen(f, 'w'); n = fprintf(fid, '%d %d\n', [1 2; 3 4]); fclose(fid); fid = fopen(f); A = fscanf(fid, '%d', [2 Inf])'; fclose(fid); delete(f);"
    Then variable "n" equals row [8]
    And variable "A" equals row [1, 3, 2, 4]

  @needs_numpy
  Scenario: save and load round-trip
    Given a fresh session
    When I evaluate "m = [tempname '.mat']; X = [1 2 3]; Y = 5; save(m, 'X', 'Y'); clear X Y; load(m); Z = [X Y]; delete(m);"
    Then variable "Z" equals row [1, 2, 3, 5]

  @needs_numpy
  Scenario: load into a struct with selection
    Given a fresh session
    When I evaluate "m = [tempname '.mat']; a = 1; b = 2; save(m); S = load(m, 'b'); k = isfield(S, 'a'); v = S.b; delete(m);"
    Then variable "k" equals row [0]
    And variable "v" equals row [2]

  @needs_numpy
  Scenario: sscanf and binary fwrite/fread
    Given a fresh session
    When I evaluate "x = sscanf('1.5,2.5,3', '%f,')'; g = [tempname '.bin']; fid = fopen(g, 'w'); fwrite(fid, [-1 300], 'int16'); fclose(fid); fid = fopen(g); y = fread(fid, Inf, 'int16')'; fclose(fid); delete(g);"
    Then variable "x" equals row [1.5, 2.5, 3]
    And variable "y" equals row [-1, 300]

  @needs_numpy
  Scenario: missing file gives fid -1
    Given a fresh session
    When I evaluate "fid = fopen('/no/such/dir/q.txt', 'r');"
    Then variable "fid" equals row [-1]
