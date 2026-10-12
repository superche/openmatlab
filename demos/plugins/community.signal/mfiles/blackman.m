function w = blackman(n)
%BLACKMAN  Blackman window (clean-room; public MATLAB/Octave doc semantics).
%   w = blackman(n) returns an n-point symmetric Blackman window (column).
%
%   Compatible with Octave Forge / MATLAB signal window API. Original MIT
%   work — not a copy of GPL Octave Forge sources.
%   Formula: w(k) = 0.42 - 0.5*cos(2*pi*(k-1)/(n-1)) + 0.08*cos(4*pi*(k-1)/(n-1)).
%
%   See also HAMMING, RECTWIN.

if n < 1
  w = zeros(0, 1);
  return
end
if n == 1
  w = 1;
  return
end
k = (0:n-1)';
a = (2 .* pi .* k) ./ (n - 1);
w = 0.42 - 0.5 .* cos(a) + 0.08 .* cos(2 .* a);
end
