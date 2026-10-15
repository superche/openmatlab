function [h, w] = freqz(b, a, n, opt)
%FREQZ  Frequency response of a digital filter (clean-room; public doc semantics).
%   [h, w] = freqz(b, a, n) evaluates H(e^{jw}) = B(e^{jw})/A(e^{jw}) at n
%   points w = (0:n-1)'*pi/n on the upper half of the unit circle (default
%   n = 512). freqz(b, a, n, 'whole') uses the whole circle, w = (0:n-1)'*2*pi/n.
%   freqz(b, a, w) with a vector w (two or more elements) evaluates at those
%   frequencies (rad/sample). With no output arguments it plots the magnitude
%   response in dB.
%
%   Original MIT work for OpenMATLAB, not a copy of GPL Octave Forge sources.
%
%   See also BUTTER, FILTER.

if nargin < 2 || isempty(a)
  a = 1;
end
if nargin < 3 || isempty(n)
  n = 512;
end
whole = nargin >= 4 && ischar(opt) && strcmpi(opt, 'whole');
if isscalar(n)
  if n ~= fix(n) || n < 1
    error('signal:freqz:invalidN', 'Number of frequency points must be a positive integer.');
  end
  if whole
    w = (0:n-1)' .* (2 * pi / n);
  else
    w = (0:n-1)' .* (pi / n);
  end
else
  w = n(:);
end
zinv = exp(-1i .* w);
B = zeros(size(w));
for k = numel(b):-1:1
  B = B .* zinv + b(k);
end
A = zeros(size(w));
for k = numel(a):-1:1
  A = A .* zinv + a(k);
end
hh = B ./ A;
if nargout == 0
  plot(w ./ pi, 20 .* log10(abs(hh)));
  xlabel('Normalized Frequency (\times\pi rad/sample)');
  ylabel('Magnitude (dB)');
  return
end
h = hh;
if ~isscalar(n) && size(n, 1) == 1
  h = h.';
  w = w.';
end
end
