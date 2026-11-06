Feature: writetable and writecell QuoteStrings (issue #1047)
  @needs_numpy
  Scenario: QuoteStrings all quotes text and leaves numbers and logicals alone
    Given a fresh session
    When I evaluate "f = [tempname '.csv']; T = table(['M';'F';'M'],[45;41;36], {'New York, NY';'San Diego, CA';'Boston, MA'},[true;false;false]); writetable(T, f, 'Delimiter', ',', 'QuoteStrings', 'all'); txt = fileread(f); q = char(34); nl = sprintf('\n'); exp = ['Var1,Var2,Var3,Var4' nl q 'M' q ',45,' q 'New York, NY' q ',1' nl q 'F' q ',41,' q 'San Diego, CA' q ',0' nl q 'M' q ',36,' q 'Boston, MA' q ',0' nl]; ok = double(strcmp(txt, exp)); delete(f);"
    Then variable "ok" equals row [1]

  @needs_numpy
  Scenario: QuoteStrings none does not quote a comma and minimal does
    Given a fresh session
    When I evaluate "f = [tempname '.csv']; T = table({'New York, NY';'LA'}); writetable(T, f, 'QuoteStrings', 'none'); none = fileread(f); writetable(T, f, 'QuoteStrings', 'minimal'); mini = fileread(f); q = char(34); nl = sprintf('\n'); ok = double(strcmp(none, ['Var1' nl 'New York, NY' nl 'LA' nl]) && strcmp(mini, ['Var1' nl q 'New York, NY' q nl 'LA' nl])); delete(f);"
    Then variable "ok" equals row [1]

  @needs_numpy
  Scenario: writecell QuoteStrings all quotes text elements only
    Given a fresh session
    When I evaluate "f = [tempname '.csv']; writecell({'NY', 45; 'a,b', false}, f, 'QuoteStrings', 'all'); txt = fileread(f); q = char(34); nl = sprintf('\n'); ok = double(strcmp(txt, [q 'NY' q ',45' nl q 'a,b' q ',0' nl])); delete(f);"
    Then variable "ok" equals row [1]
