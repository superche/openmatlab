% M7 C09 - dense decompositions
A = [4 1; 2 3];
e = eig(A);
[V, D] = eig(A);
r1 = norm(A*V - V*D) < 1e-10;
es = eig([2 1; 1 2]);
s = svd([3 0; 0 4]);
[U, Sg, W] = svd(magic(3));
r2 = norm(U*Sg*W' - magic(3)) < 1e-10;
[L, U2, P] = lu([1 2; 3 4]);
r3 = norm(P*[1 2; 3 4] - L*U2) < 1e-12;
R = chol([4 2; 2 3]);
[Q, R2] = qr([1 2; 3 4]);
r4 = norm(Q*R2 - [1 2; 3 4]) < 1e-12;
r5 = norm(Q'*Q - eye(2)) < 1e-12;
N = null([1 1; 1 1]);
r6 = norm([1 1; 1 1]*N) < 1e-12 && size(N, 2) == 1;
O = orth([1 1; 1 1]);
r7 = size(O, 2) == 1;
tr = trace(magic(3));
cr = cross([1 0 0], [0 1 0]);
dt = dot([1 2 3], [4 5 6]);
try
  chol([1 2; 2 1]);
catch err
  pd = strcmp(err.identifier, 'MATLAB:posdef');
end
ce = eig([0 -1; 1 0]);
ce_ok = isequal(sort(imag(ce)), [-1; 1]);
