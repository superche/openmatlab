Feature: readtable Range for delimited text (issue #1041)
  @needs_numpy
  Scenario: a rectangular Range drops the rows and columns outside it
    Given a fresh session
    When I evaluate "f = [tempname '.csv']; fid = fopen(f,'w'); fprintf(fid,'skip,me\nid,name,score\n1,ann,10\n2,bob,20\n3,cy,30\n'); fclose(fid); T = readtable(f,'Range','B2:C4'); v = T.score'; delete(f);"
    Then variable "v" equals row [10, 20]

  @needs_numpy
  Scenario: detectImportOptions Range is what readtable uses
    Given a fresh session
    When I evaluate "f = [tempname '.csv']; fid = fopen(f,'w'); fprintf(fid,'id,name,score\n1,ann,10\n2,bob,20\n'); fclose(fid); opts = detectImportOptions(f,'Range','B:C'); T = readtable(f,opts); v = T.score'; delete(f);"
    Then variable "v" equals row [10, 20]
