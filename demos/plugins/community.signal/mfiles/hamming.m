function w = hamming(n)
%HAMMING  Hamming window (clean-room; public MATLAB/Octave doc semantics).
%   w = hamming(n) returns an n-point symmetric Hamming window (column).
%
%   Compatible with the well-known Octave Forge / MATLAB signal window API.
%   This file is original MIT work for OpenMATLAB — not a copy of GPL Octave
%   Forge sources. Formula: w(k) = 0.54 - 0.46*cos(2*pi*(k-1)/(n-1)), k=1..n.
%
%   See also RECTWIN, BLACKMAN.

if n < 1
  w = zeros(0, 1);
  return
end
if n == 1
  w = 1;
  return
end
k = (0:n-1)';
w = 0.54 - 0.46 .* cos((2 .* pi .* k) ./ (n - 1));
end
