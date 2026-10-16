% M10 T06 - join, innerjoin, outerjoin
A = table([1;2;3], [10;20;30], 'VariableNames', {'k','x'});
B = table([3;1;4], [300;100;400], 'VariableNames', {'k','y'});
I = innerjoin(A, B);
j1 = I.k';
j2 = I.y';
O = outerjoin(A, B, 'MergeKeys', true);
j3 = height(O);
j4 = O.k';
j5 = sum(isnan(O.y));
j6 = sum(isnan(O.x));
L = outerjoin(A, B, 'Type', 'left', 'MergeKeys', true);
j7 = height(L);
C = table([1;2;3], [7;8;9], 'VariableNames', {'k','z'});
J = join(A, C);
j8 = J.z';
j9 = width(J);
j10 = 0;
try
  join(A, B);
catch
  j10 = 1;
end
O2 = outerjoin(A, B);
j11 = width(O2);
J2 = innerjoin(A, B, 'Keys', 'k');
j12 = height(J2);
