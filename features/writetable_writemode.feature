Feature: writetable WriteMode for delimited text (issue #1048)
  @needs_numpy
  Scenario: Append adds a row and keeps the header written earlier
    Given a fresh session
    When I evaluate "f = [tempname '.txt']; T = table({'Monarch Butterfly';'Seven-spot Ladybird'}, {'Lepidoptera';'Coleoptera'}, [false;true], 'VariableNames', {'InsectSpecies','InsectOrder','PredatoryInsect'}); writetable(T, f, 'WriteRowNames', true); writetable(table({'Red-banded leafhopper'},{'Hemiptera'},false), f, 'WriteMode', 'Append', 'WriteVariableNames', false, 'WriteRowNames', true); txt = fileread(f); nl = sprintf('\n'); exp = ['InsectSpecies,InsectOrder,PredatoryInsect' nl 'Monarch Butterfly,Lepidoptera,0' nl 'Seven-spot Ladybird,Coleoptera,1' nl 'Red-banded leafhopper,Hemiptera,0' nl]; ok = double(strcmp(txt, exp)); delete(f);"
    Then variable "ok" equals row [1]

  @needs_numpy
  Scenario: Overwrite replaces a file and append creates one with no header
    Given a fresh session
    When I evaluate "f = [tempname '.csv']; writetable(table([1;2]), f); writetable(table([9]), f, 'WriteMode', 'overwrite'); over = fileread(f); delete(f); writetable(table([3;4]), f, 'WriteMode', 'append', 'WriteVariableNames', false); made = fileread(f); nl = sprintf('\n'); ok = double(strcmp(over, ['Var1' nl '9' nl]) && strcmp(made, ['3' nl '4' nl])); delete(f);"
    Then variable "ok" equals row [1]
