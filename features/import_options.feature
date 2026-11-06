Feature: delimited-text import options (issue #1040)
  @needs_numpy
  Scenario: setvaropts TreatAsMissing and a variable subset import through readtable
    Given a fresh session
    When I evaluate "f = [tempname '.csv']; fid = fopen(f,'w'); fprintf(fid,'id,score\n1,10\n2,NA\n3,4\n'); fclose(fid); opts = detectImportOptions(f); opts = setvaropts(opts,'score','Type','double','TreatAsMissing','NA'); opts.SelectedVariableNames = {'score'}; T = readtable(f,opts); m = double(ismissing(T.score')); delete(f);"
    Then variable "m" equals row [0, 1, 0]
