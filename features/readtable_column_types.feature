Feature: readtable duration, logical, and categorical columns (issue #1046)
  @needs_numpy
  Scenario: A clock without seconds is datetime and timer text is duration
    Given a fresh session
    When I evaluate "f = [tempname '.csv']; fid = fopen(f,'w'); fprintf(fid,'when,elapsed\n2002-02-01 12:18,01:02:03\n2002-02-07 16:50,1:00:00:00\n'); fclose(fid); T = readtable(f); k = double([isdatetime(T.when) isduration(T.elapsed)]); s = round(seconds(T.elapsed)'); delete(f);"
    Then variable "k" equals row [1, 1]
    And variable "s" equals row [3723, 86400]

  @needs_numpy
  Scenario: true and false become logical only after the type is set
    Given a fresh session
    When I evaluate "f = [tempname '.csv']; fid = fopen(f,'w'); fprintf(fid,'flag,region\nTRUE,South\nfalse,North\n'); fclose(fid); opts = detectImportOptions(f); c = double(strcmp(opts.VariableTypes{1},'char') && strcmp(opts.VariableTypes{2},'char')); opts = setvaropts(opts,'flag','Type','logical'); opts = setvaropts(opts,'region','Type','categorical'); T = readtable(f,opts); b = double(T.flag)'; delete(f);"
    Then variable "c" equals row [1]
    And variable "b" equals row [1, 0]
