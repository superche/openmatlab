function w = kaiser(n, beta)
%KAISER  Kaiser window (clean-room; public MATLAB/Octave doc semantics).
%   w = kaiser(n, beta) returns an n-point Kaiser window (column) with shape
%   parameter beta (default 0.5).
%
%   Original MIT work for OpenMATLAB, not a copy of GPL Octave Forge sources.
%   Formula: w(k) = I0(beta*sqrt(1 - ((k - M)/M)^2)) / I0(beta), M = (n-1)/2,
%   with I0 the zeroth-order modified Bessel function of the first kind,
%   evaluated here by its power series sum((x/2)^(2j) / (j!)^2).
%
%   See also HANN, HAMMING.

if nargin < 2
  beta = 0.5;
end
if ~isscalar(n) || n ~= fix(n) || n < 0
  error('signal:kaiser:invalidLength', 'Window length must be a nonnegative integer scalar.');
end
if ~isscalar(beta) || ~isreal(beta) || beta < 0
  error('signal:kaiser:invalidBeta', 'Beta must be a nonnegative real scalar.');
end
if n == 0
  w = zeros(0, 1);
  return
end
if n == 1
  w = 1;
  return
end
M = (n - 1) / 2;
k = (0:n-1)';
t = beta .* sqrt(max(0, 1 - ((k - M) ./ M) .^ 2));
w = besseli0(t) ./ besseli0(beta);
end

function y = besseli0(x)
% Power series of I0; terms shrink fast for the beta range used by windows.
y = ones(size(x));
term = ones(size(x));
for j = 1:200
  term = term .* (x ./ 2) .^ 2 ./ (j * j);
  y = y + term;
  if all(term(:) <= eps .* y(:))
    break
  end
end
end
