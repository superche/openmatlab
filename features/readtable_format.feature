Feature: readtable Format for delimited text (issue #1042)
  @needs_numpy
  Scenario: a textscan Format types each delimited column
    Given a fresh session
    When I evaluate "f = [tempname '.csv']; fid = fopen(f,'w'); fprintf(fid,'LastName,Gender,Age,Height,Weight,Smoker\nSmith,M,38,71,176,1\nJohnson,M,43,69,163,0\n'); fclose(fid); T = readtable(f,'Format','%s%s%u%f%f%s'); v = double(T.Age)'; k = double(strcmp(class(T.Age),'uint32')); c = double(iscell(T.LastName)); delete(f);"
    Then variable "v" equals row [38, 43]
    And variable "k" equals row [1]
    And variable "c" equals row [1]

  @needs_numpy
  Scenario: Format auto keeps a blank field as text
    Given a fresh session
    When I evaluate "f = [tempname '.csv']; fid = fopen(f,'w'); fprintf(fid,'id,score\n1,\n2,4\n'); fclose(fid); A = readtable(f); B = readtable(f,'Format','auto'); na = double(isnan(A.score')); cb = double(iscell(B.score)); delete(f);"
    Then variable "na" equals row [1, 0]
    And variable "cb" equals row [1]
