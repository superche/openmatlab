function b = resize(a, varargin)
% RESIZE  Octave pad/truncate to a size, test vocabulary shim for the T2 harness.
if numel(varargin) == 1
    sz = varargin{1};
    if isscalar(sz)
        sz = [sz sz];
    end
else
    sz = [varargin{:}];
end
if isnumeric(a) || islogical(a)
    b = zeros(sz, 'like', a);
elseif iscell(a)
    b = cell(sz);
elseif isstruct(a)
    f = fieldnames(a);
    blank = cell2struct(cell(numel(f), 1), f, 1);
    b = repmat(blank, sz);
else
    b = repmat(char(0), sz);
end
n = min([size(a), ones(1, numel(sz) - ndims(a))], sz);
idx = arrayfun(@(k) 1:n(k), 1:numel(sz), 'UniformOutput', false);
if all(n > 0)
    b(idx{:}) = a(idx{:});
end
end
