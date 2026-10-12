% for / while / if / switch
s = 0;
for i = 1:5
  if mod(i, 2) == 0
    s = s + i;
  end
end
k = 0;
while k < 3
  k = k + 1;
end
switch k
  case 3
    label = 30;
  otherwise
    label = 0;
end
