classdef TallyDemo
  % O-E4 demo: subsref/subsasgn overloads with builtin() fallback
  properties
    counts = struct()
  end
  methods
    function v = subsref(obj, s)
      if strcmp(s(1).type, '{}')
        k = s(1).subs{1};
        if isfield(obj.counts, k), v = obj.counts.(k); else, v = 0; end
      else
        v = builtin('subsref', obj, s);
      end
    end
    function obj = subsasgn(obj, s, val)
      if strcmp(s(1).type, '{}')
        obj.counts.(s(1).subs{1}) = val;
      else
        obj = builtin('subsasgn', obj, s, val);
      end
    end
  end
end
