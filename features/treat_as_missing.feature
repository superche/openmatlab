Feature: readtable TreatAsMissing on CSV (issue #721, epic #1032)
  @needs_numpy
  Scenario: sentinel tokens become missing, then rmmissing and fillmissing run
    Given a fresh session
    When I evaluate "f = [tempname '.csv']; fid = fopen(f,'w'); fprintf(fid,'id,score\n1,10\n2,NA\n3,-999\n4,\n'); fclose(fid); T = readtable(f,'TreatAsMissing',{'NA','-999',''}); m = double(ismissing(T)); R = rmmissing(T); h = height(R); rid = R.id'; F = fillmissing(T,'previous'); fs = F.score'; delete(f);"
    Then variable "m" equals row [0, 0, 0, 1, 0, 1, 0, 1]
    And variable "h" equals row [1]
    And variable "rid" equals row [1]
    And variable "fs" equals row [10, 10, 10, 10]
