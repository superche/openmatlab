function y = filtfilt(b, a, x)
%FILTFILT  Zero-phase digital filtering (clean-room; public doc semantics).
%   y = filtfilt(b, a, x) filters x forward and then backward with the filter
%   b/a, so the result has zero phase distortion and the squared magnitude
%   response. Vectors keep their orientation; matrices are filtered column by
%   column.
%
%   Original MIT work for OpenMATLAB, not a copy of GPL Octave Forge sources.
%   Method (Gustafsson's initial conditions, as documented for MATLAB's
%   filtfilt): the signal is extended at both ends by 3*(nfilt-1) samples of
%   odd reflection, and each pass starts from the filter's steady-state
%   initial conditions scaled by the first sample, which suppresses edge
%   transients. The extension is removed at the end.
%
%   See also FILTER, BUTTER.

if nargin < 3
  error('signal:filtfilt:notEnoughInputs', 'Not enough input arguments.');
end
b = b(:).';
a = a(:).';
if isempty(a) || a(1) == 0
  error('signal:filtfilt:invalidA', 'First denominator filter coefficient must be non-zero.');
end
b = b ./ a(1);
a = a ./ a(1);
nf = max(numel(b), numel(a));
if numel(b) < nf, b(nf) = 0; end
if numel(a) < nf, a(nf) = 0; end
nfact = 3 * (nf - 1);
isrow_in = isvector(x) && size(x, 1) == 1;
if isrow_in
  x = x(:);
end
if size(x, 1) <= nfact
  error('signal:filtfilt:InvalidDimensions', 'Data must have length more than 3 times filter order.');
end
if nf > 1
  M = eye(nf - 1) - [-a(2:nf).', [eye(nf - 2); zeros(1, nf - 2)]];
  zi = M \ (b(2:nf) - b(1) .* a(2:nf)).';
else
  zi = zeros(0, 1);
end
y = zeros(size(x));
for c = 1:size(x, 2)
  xc = x(:, c);
  if nfact > 0
    ext = [2 * xc(1) - xc(nfact+1:-1:2); xc; 2 * xc(end) - xc(end-1:-1:end-nfact)];
  else
    ext = xc;
  end
  v = filter(b, a, ext, zi .* ext(1));
  v = flipud(v);
  v = filter(b, a, v, zi .* v(1));
  v = flipud(v);
  y(:, c) = v(nfact+1:end-nfact);
end
if isrow_in
  y = y.';
end
end
