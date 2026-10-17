function t2_assert(cond, varargin)
% T2_ASSERT  Octave-style assert used by the T2 self-check harness (M12 C07, #765).
%   t2_assert(cond), t2_assert(cond, errmsg, ...)   condition form
%   t2_assert(observed, expected [, tol])            comparison form; tol > 0 absolute,
%                                                    tol < 0 relative, 0 exact.
% Own implementation; failures never echo values (the harness stores pass/fail only).
if nargin == 1 || (nargin > 1 && islogical(cond) && ischar(varargin{1}))
    if isempty(cond) || ~all(cond(:))
        if nargin > 1
            error('openmatlab:t2:assert', 'assert: condition failed (custom message)');
        end
        error('openmatlab:t2:assert', 'assert: condition failed');
    end
    return
end
tol = 0;
if nargin > 2
    tol = varargin{2};
end
why = t2_compare(cond, varargin{1}, tol);
if ~isempty(why)
    error('openmatlab:t2:assert', ['assert: ' why]);
end
end

function why = t2_compare(obs, expc, tol)
why = '';
if ischar(expc)
    if ~ischar(obs)
        why = 'expected char';
    elseif ~isequal(size(obs), size(expc)) || ~all(obs(:) == expc(:))
        why = 'char mismatch';
    end
elseif iscell(expc)
    if ~iscell(obs)
        why = 'expected cell';
    elseif ~isequal(size(obs), size(expc))
        why = 'cell size mismatch';
    else
        for k = 1:numel(expc)
            why = t2_compare(obs{k}, expc{k}, tol);
            if ~isempty(why)
                return
            end
        end
    end
elseif isstruct(expc)
    if ~isstruct(obs)
        why = 'expected struct';
    elseif ~isequal(size(obs), size(expc)) || ~isequal(sort(fieldnames(obs)), sort(fieldnames(expc)))
        why = 'struct shape mismatch';
    else
        f = fieldnames(expc);
        for k = 1:numel(expc)
            for j = 1:numel(f)
                why = t2_compare(obs(k).(f{j}), expc(k).(f{j}), tol);
                if ~isempty(why)
                    return
                end
            end
        end
    end
elseif isnumeric(expc) || islogical(expc)
    if ~(isnumeric(obs) || islogical(obs))
        why = 'expected numeric';
        return
    end
    if ~isequal(size(obs), size(expc))
        why = 'size mismatch';
        return
    end
    if ~strcmp(class(obs), class(expc)) && ~(islogical(obs) && islogical(expc))
        why = 'class mismatch';
        return
    end
    if isempty(expc)
        return
    end
    o = double(obs(:));
    e = double(expc(:));
    t = double(tol(:));
    if isscalar(t)
        t = t * ones(size(e));
    end
    nan_o = isnan(o);
    nan_e = isnan(e);
    if any(nan_o ~= nan_e)
        why = 'NaN mismatch';
        return
    end
    inf_e = isinf(e);
    if any(isinf(o) ~= inf_e) || any(o(inf_e) ~= e(inf_e))
        why = 'Inf mismatch';
        return
    end
    m = ~nan_e & ~inf_e;
    d = abs(o(m) - e(m));
    tm = t(m);
    rel = tm < 0;
    lim = abs(tm);
    if any(rel)
        em = e(m);
        lim(rel) = abs(tm(rel)) .* abs(em(rel));
    end
    if any(d > lim)
        why = 'values differ beyond tolerance';
    end
else
    if ~isequal(obs, expc)
        why = 'objects differ';
    end
end
end
