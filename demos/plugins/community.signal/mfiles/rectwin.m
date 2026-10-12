function w = rectwin(n)
%RECTWIN  Rectangular window (clean-room; public MATLAB/Octave doc semantics).
%   w = rectwin(n) returns an n-point rectangular window (column of ones).
%
%   Compatible with Octave Forge / MATLAB signal window API. Original MIT
%   work — not a copy of GPL Octave Forge sources.
%
%   See also HAMMING, BLACKMAN.

if n < 1
  w = zeros(0, 1);
  return
end
w = ones(n, 1);
end
