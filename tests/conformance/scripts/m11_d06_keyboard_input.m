% M11 D06 - input, input(...,'s'), empty input, keyboard + dbcont
% Console input comes from m11_d06_keyboard_input.queue.
d = tempname; mkdir(d);
wf_d06(d, 'kb_d06', { ...
  'function r = kb_d06()', ...
  '  v = 1;', ...
  '  keyboard', ...
  '  r = v;', ...
  'end'});
addpath(d);
x = input('Enter: ');
n1 = x;
s = input('Name: ', 's');
n2 = double(strcmp(s, 'hello'));
e = input('');
n3 = double(isempty(e));
n4 = kb_d06();
n5 = double(ischar(s));
rmpath(d);

function wf_d06(d, name, lines)
  fid = fopen(fullfile(d, [name '.m']), 'w');
  fprintf(fid, '%s\n', lines{:});
  fclose(fid);
end
