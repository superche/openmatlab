s = 0;
for i = 1:10
  if mod(i,2) == 0
    continue;
  end
  if i > 7
    break;
  end
  s = s + i;
end
k = 0;
while k < 3
  k = k + 1;
end
switch k
  case {1,2}
    t = 1;
  otherwise
    t = 2;
end
