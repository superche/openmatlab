function [b, a] = butter(n, Wn, ftype)
%BUTTER  Butterworth digital filter design (clean-room; public doc semantics).
%   [b, a] = butter(n, Wn) designs an order-n lowpass digital Butterworth
%   filter with normalized cutoff Wn (0 < Wn < 1, 1 = Nyquist).
%   [b, a] = butter(n, Wn, 'high') designs a highpass filter.
%   ('low' is also accepted.)
%
%   Original MIT work for OpenMATLAB, not a copy of GPL Octave Forge sources.
%   Method: analog prototype poles p_k = exp(1i*pi*(2k+n-1)/(2n)), k = 1..n,
%   prewarped cutoff Omega = tan(pi*Wn/2), bilinear map z = (1+s)/(1-s);
%   zeros at z = -1 (lowpass) or z = +1 (highpass); gain normalized to 1 at
%   DC (lowpass) or Nyquist (highpass).
%
%   See also FREQZ, FILTFILT, FILTER.

if nargin < 2
  error('signal:butter:notEnoughInputs', 'Not enough input arguments.');
end
if nargin < 3
  ftype = 'low';
end
if ~isscalar(n) || n ~= fix(n) || n < 1
  error('signal:butter:invalidOrder', 'Filter order must be a positive integer.');
end
if ~isscalar(Wn) || Wn <= 0 || Wn >= 1
  error('signal:butter:invalidCutoff', 'The cutoff frequency Wn must be a scalar with 0 < Wn < 1.');
end
k = (1:n)';
p = exp(1i .* pi .* (2 .* k + n - 1) ./ (2 .* n));
Omega = tan(pi .* Wn ./ 2);
switch lower(ftype)
  case 'low'
    s = Omega .* p;
    zr = -ones(n, 1);
    zref = 1;
  case 'high'
    s = Omega ./ p;
    zr = ones(n, 1);
    zref = -1;
  otherwise
    error('signal:butter:invalidType', 'Filter type must be ''low'' or ''high''.');
end
pz = (1 + s) ./ (1 - s);
a = real(poly(pz));
b = real(poly(zr));
b = b .* (polyval(a, zref) ./ polyval(b, zref));
end
