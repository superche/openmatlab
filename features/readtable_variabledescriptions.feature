Feature: readtable stores original headers in VariableDescriptions (issue #1045)
  @needs_numpy
  Scenario: a rewritten header is saved and a preserved header is not
    Given a fresh session
    When I evaluate "f = [tempname '.csv']; fid = fopen(f,'w'); fprintf(fid,'id,Last Name\n1,Ada\n'); fclose(fid); lastwarn('',''); M = readtable(f); [w, id] = lastwarn; P = readtable(f,'VariableNamingRule','preserve'); a = double(strcmp(M.Properties.VariableNames{2},'LastName') && strcmp(M.Properties.VariableDescriptions{1},'id') && strcmp(M.Properties.VariableDescriptions{2},'Last Name') && strcmp(id,'MATLAB:table:ModifiedAndSavedVarnames') && ~isempty(w)); b = double(strcmp(P.Properties.VariableNames{2},'Last Name') && isempty(P.Properties.VariableDescriptions)); delete(f);"
    Then variable "a" equals row [1]
    And variable "b" equals row [1]
