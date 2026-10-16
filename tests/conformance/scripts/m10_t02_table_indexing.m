% M10 T02 - table indexing, assignment, deletion, concatenation
T = table([1;2;3], [4;5;6], 'VariableNames', {'a','b'});
i1 = T.a(2);
i2 = T{3,'b'};
S = T(2:3,:);
i3 = height(S);
i4 = T{2,2};
R = T(T.a > 1, :);
i5 = sum(R.b);
T.c = T.a + T.b;
i6 = width(T);
i7 = T.c(end);
T.b = [];
i8 = width(T);
T(1,:) = [];
i9 = height(T);
i10 = T{end,'a'};
U = [T; T];
i11 = height(U);
V = table([7;8], 'VariableNames', {'z'});
W = [T V];
i12 = width(W);
i13 = 0;
try
  X = [T; V];
catch
  i13 = 1;
end
i14 = 0;
try
  Y = [T T];
catch
  i14 = 1;
end
T{1,'a'} = 100;
i15 = T.a(1);
T(3,:) = {9, 99};
i16 = T.c(3);
i17 = istable(T(:,'a'));
