function w = hann(n, sflag)
%HANN  Hann (Hanning) window (clean-room; public MATLAB/Octave doc semantics).
%   w = hann(n) returns an n-point symmetric Hann window (column).
%   w = hann(n, 'periodic') returns the periodic version (for spectral analysis).
%
%   Original MIT work for OpenMATLAB, not a copy of GPL Octave Forge sources.
%   Formula: w(k) = 0.5 - 0.5*cos(2*pi*k/m), k = 0..n-1, m = n-1 (symmetric) or n (periodic).
%
%   See also HAMMING, KAISER, BLACKMAN.

if nargin < 2
  sflag = 'symmetric';
end
if ~isscalar(n) || n ~= fix(n) || n < 0
  error('signal:hann:invalidLength', 'Window length must be a nonnegative integer scalar.');
end
if n == 0
  w = zeros(0, 1);
  return
end
if n == 1
  w = 1;
  return
end
switch lower(sflag)
  case 'symmetric'
    m = n - 1;
  case 'periodic'
    m = n;
  otherwise
    error('signal:hann:invalidFlag', 'Sampling flag must be ''symmetric'' or ''periodic''.');
end
k = (0:n-1)';
w = 0.5 - 0.5 .* cos((2 .* pi .* k) ./ m);
end
