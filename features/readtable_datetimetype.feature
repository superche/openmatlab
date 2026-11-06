Feature: readtable DatetimeType for delimited text (issue #1043)
  @needs_numpy
  Scenario: DatetimeType text keeps the date characters and the numeric column
    Given a fresh session
    When I evaluate "f = [tempname '.csv']; fid = fopen(f,'w'); fprintf(fid,'id,when\n1,2020-01-02\n2,2020-03-04\n'); fclose(fid); A = readtable(f); T = readtable(f,'DatetimeType','text'); n = double(T.id'); d0 = double(isdatetime(A.when)); c = double(iscell(T.when)); k = double(strcmp(T.when{1},'2020-01-02') && strcmp(T.when{2},'2020-03-04')); delete(f);"
    Then variable "n" equals row [1, 2]
    And variable "d0" equals row [1]
    And variable "c" equals row [1]
    And variable "k" equals row [1]

  @needs_numpy
  Scenario: detectImportOptions DatetimeType text is what readtable uses
    Given a fresh session
    When I evaluate "f = [tempname '.csv']; fid = fopen(f,'w'); fprintf(fid,'id,when\n1,2020-01-02\n'); fclose(fid); opts = detectImportOptions(f,'DatetimeType','text','TextType','string'); T = readtable(f,opts); k = double(strcmp(opts.VariableTypes{2},'string') && strcmp(class(T.when),'string')); delete(f);"
    Then variable "k" equals row [1]
