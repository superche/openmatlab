Feature: readtable VariableNamingRule for delimited text (issue #1044)
  @needs_numpy
  Scenario: preserve keeps the header and modify still makes a valid name
    Given a fresh session
    When I evaluate "f = [tempname '.csv']; fid = fopen(f,'w'); fprintf(fid,'id,Last Name\n1,Ada\n'); fclose(fid); M = readtable(f); P = readtable(f,'VariableNamingRule','preserve'); a = double(strcmp(M.Properties.VariableNames{2},'LastName') && M.id==1); b = double(strcmp(P.Properties.VariableNames{1},'id') && strcmp(P.Properties.VariableNames{2},'Last Name') && P.id==1); delete(f);"
    Then variable "a" equals row [1]
    And variable "b" equals row [1]

  @needs_numpy
  Scenario: detectImportOptions records preserve and readtable uses it
    Given a fresh session
    When I evaluate "f = [tempname '.csv']; fid = fopen(f,'w'); fprintf(fid,'id,Last Name\n4,Ada\n'); fclose(fid); opts = detectImportOptions(f,'VariableNamingRule','preserve'); T = readtable(f,opts); k = double(strcmp(opts.VariableNamingRule,'preserve') && strcmp(opts.VariableNames{2},'Last Name') && strcmp(T.Properties.VariableNames{2},'Last Name') && T.id==4); delete(f);"
    Then variable "k" equals row [1]
