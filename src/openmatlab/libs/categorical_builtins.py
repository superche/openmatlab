"""categorical builtins (M10 T-E2, Epic #692)."""

from __future__ import annotations

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue
from openmatlab.runtime.categorical_value import UNDEF, CategoricalValue, categories_value
from openmatlab.runtime.table_value import _cv, _err, cellstr_col, is_text, text, texts


def _bool(b):
    return NDArrayValue(np.asarray(b, dtype=bool).reshape(np.shape(b) or (1, 1)))


def _num(a):
    return NDArrayValue(np.asarray(a, dtype=float))


def _need(args, fn, n=1):
    if len(args) < n or not isinstance(args[0], CategoricalValue):
        raise _err(f"First input to {fn} must be a categorical array.", f"MATLAB:categorical:{fn}:InvalidInput")
    return args[0]


def _flag(v):
    return bool(np.asarray(v.backend_buffer()).reshape(-1)[0])


def _numtext(x):
    x = float(x)
    return str(int(x)) if x == int(x) else f"{x:.5g}"


def _keys(v):
    """data or valueset -> (list of hashable keys or None for missing, shape, is_numeric)."""
    from openmatlab.runtime.cell_value import CellValue

    if isinstance(v, CategoricalValue):
        return [None if s == UNDEF else s for s in v.labels()], v.shape, False
    t = texts(v)
    if t is not None:
        shape = (1, 1) if is_text(v) else tuple(v.shape)
        miss = None
        if getattr(v, "is_string", False):
            from openmatlab.runtime import string_array as sa

            grid = np.asarray(sa.to_grid(v), dtype=object).reshape(-1, order="F")
            miss = [g is None for g in grid]
        out = [None if (s == "" or (miss and miss[k])) else s for k, s in enumerate(t)]
        return out, shape, False
    if isinstance(v, CellValue):
        raise _err("Data input must be a numeric, logical, string, or categorical array, or a cell array of "
                   "character vectors.", "MATLAB:categorical:InvalidData")
    if hasattr(v, "backend_buffer") and not getattr(v, "is_object", False):
        a = np.asarray(v.backend_buffer())
        if np.iscomplexobj(a):
            raise _err("Data input must not be complex.", "MATLAB:categorical:InvalidData")
        f = a.astype(float).reshape(-1, order="F")
        if a.dtype == np.bool_:
            return ["true" if x else "false" for x in f], tuple(a.shape), False
        return [None if np.isnan(x) else float(x) for x in f], tuple(a.shape), True
    raise _err("Data input must be a numeric, logical, string, or categorical array, or a cell array of "
               "character vectors.", "MATLAB:categorical:InvalidData")


def _categorical(args, *, nargout=1):
    args = list(args)
    ordinal = protected = False
    while len(args) >= 3 and is_text(args[-2]) and text(args[-2]).lower() in ("ordinal", "protected"):
        if text(args[-2]).lower() == "ordinal":
            ordinal = _flag(args[-1])
        else:
            protected = _flag(args[-1])
        args = args[:-2]
    if len(args) == 3 and is_text(args[1]) and text(args[1]).lower() in ("ordinal", "protected"):
        pass
    if not args:
        return (CategoricalValue(np.zeros((0, 0)), [], ordinal, protected),)
    if len(args) > 3:
        raise _err("Too many input arguments.", "MATLAB:TooManyInputs")
    keys, shape, numeric = _keys(args[0])
    if len(args) >= 2:
        vs, _s, vnum = _keys(args[1])
        if any(k is None for k in vs):
            raise _err("VALUESET must not contain missing values.", "MATLAB:categorical:MissingValueset")
        if len(set(vs)) != len(vs):
            raise _err("VALUESET must contain unique values.", "MATLAB:categorical:NonUniqueValueset")
        if numeric != vnum and not isinstance(args[0], CategoricalValue):
            raise _err("VALUESET must be the same type as the data.", "MATLAB:categorical:ValuesetTypeMismatch")
    else:
        if isinstance(args[0], CategoricalValue):
            vs = list(args[0].cats)
            ordinal = ordinal or args[0].ordinal
        else:
            vs = sorted({k for k in keys if k is not None})
    if len(args) == 3:
        names = texts(args[2])
        if names is None:
            raise _err("CATEGORYNAMES must be a string array or a cell array of character vectors.",
                       "MATLAB:categorical:InvalidNames")
        if len(names) != len(vs):
            raise _err("Number of category names must equal the number of values in VALUESET.",
                       "MATLAB:categorical:WrongNumCategoryNames")
        if any(n == "" for n in names):
            raise _err("Category names must be nonempty.", "MATLAB:categorical:EmptyCategoryNames")
    else:
        names = [_numtext(k) if numeric else k for k in vs]
    # duplicate names merge into one category (MATLAB allows many-to-one in CATEGORYNAMES)
    cats, where = [], {}
    for n in names:
        if n not in where:
            where[n] = len(cats) + 1
            cats.append(n)
    code_of = {k: where[n] for k, n in zip(vs, names)}
    codes = np.array([code_of.get(k, 0) if k is not None else 0 for k in keys], dtype=np.int64)
    return (CategoricalValue(codes.reshape(shape, order="F"), cats, ordinal, protected),)


def _categories(args, *, nargout=1):
    return (categories_value(_need(args, "categories")),)


def _countcats(args, *, nargout=1):
    c = _need(args, "countcats")
    k = len(c.cats)
    codes = c.codes
    dim = int(np.asarray(args[1].backend_buffer()).reshape(-1)[0]) if len(args) > 1 else (2 if codes.shape[0] == 1 else 1)
    if dim == 1:
        out = np.array([[np.sum(codes[:, j] == i + 1) for j in range(codes.shape[1])] for i in range(k)], float)
        return (_num(out.reshape(k, codes.shape[1])),)
    out = np.array([[np.sum(codes[r, :] == i + 1) for i in range(k)] for r in range(codes.shape[0])], float)
    return (_num(out.reshape(codes.shape[0], k)),)


def _cat_list(v, fn):
    t = texts(v)
    if t is None:
        raise _err(f"{fn}: categories must be specified as a string array or a cell array of character vectors.",
                   f"MATLAB:categorical:{fn}:InvalidCategories")
    return t


def _addcats(args, *, nargout=1):
    c = _need(args, "addcats", 2)
    new = _cat_list(args[1], "addcats")
    for s in new:
        if s in c.cats:
            raise _err(f"Category '{s}' is already a category.", "MATLAB:categorical:addcats:DuplicateCategories")
    cats = list(c.cats)
    rest = args[2:]
    if len(rest) == 2 and is_text(rest[0]) and text(rest[0]).lower() in ("before", "after"):
        anchor = text(rest[1])
        if anchor not in cats:
            raise _err(f"Category '{anchor}' is not a category.", "MATLAB:categorical:addcats:UnrecognizedCategory")
        pos = cats.index(anchor) + (1 if text(rest[0]).lower() == "after" else 0)
    elif rest:
        raise _err("Invalid option for addcats.", "MATLAB:categorical:addcats:InvalidOption")
    else:
        if c.ordinal:
            raise _err("You must specify 'Before' or 'After' to add categories to an ordinal categorical array.",
                       "MATLAB:categorical:addcats:NoBeforeOrAfter")
        pos = len(cats)
    old = cats
    cats = cats[:pos] + new + cats[pos:]
    return (c.like(_remap(c.codes, old, cats), cats),)


def _remap(codes, old, new):
    m = np.array([0] + [new.index(s) + 1 if s in new else 0 for s in old], dtype=np.int64)
    return m[codes]


def _removecats(args, *, nargout=1):
    c = _need(args, "removecats")
    if len(args) > 1:
        rm = _cat_list(args[1], "removecats")
    else:
        used = set(c.codes.reshape(-1).tolist())
        rm = [s for i, s in enumerate(c.cats) if i + 1 not in used]
    cats = [s for s in c.cats if s not in rm]
    return (c.like(_remap(c.codes, c.cats, cats), cats),)


def _mergecats(args, *, nargout=1):
    c = _need(args, "mergecats", 2)
    old = _cat_list(args[1], "mergecats")
    for s in old:
        if s not in c.cats:
            raise _err(f"Category '{s}' is not a category.", "MATLAB:categorical:mergecats:UnrecognizedCategory")
    new = text(args[2]) if len(args) > 2 else old[0]
    if c.ordinal:
        pos = sorted(c.cats.index(s) for s in old)
        if pos != list(range(pos[0], pos[0] + len(pos))):
            raise _err("Categories to merge in an ordinal categorical array must be consecutive.",
                       "MATLAB:categorical:mergecats:NonconsecutiveCategories")
    first = min(c.cats.index(s) for s in old)
    cats = []
    for i, s in enumerate(c.cats):
        if s in old:
            if i == first:
                cats.append(new)
        elif s == new:
            raise _err(f"Category '{new}' is already a category.", "MATLAB:categorical:mergecats:DuplicateNewCategory")
        else:
            cats.append(s)
    m = np.array([0] + [cats.index(new if s in old else s) + 1 for s in c.cats], dtype=np.int64)
    return (c.like(m[c.codes], cats),)


def _renamecats(args, *, nargout=1):
    c = _need(args, "renamecats", 2)
    if len(args) == 2:
        old, new = list(c.cats), _cat_list(args[1], "renamecats")
    else:
        old, new = _cat_list(args[1], "renamecats"), _cat_list(args[2], "renamecats")
    if len(old) != len(new):
        raise _err("Number of new category names must match the number of categories to rename.",
                   "MATLAB:categorical:renamecats:SizeMismatch")
    cats = list(c.cats)
    for o, n in zip(old, new):
        if o not in cats:
            raise _err(f"Category '{o}' is not a category.", "MATLAB:categorical:renamecats:InvalidOldNames")
        cats[cats.index(o)] = n
    if len(set(cats)) != len(cats):
        raise _err("New category names must be unique.", "MATLAB:categorical:renamecats:DuplicateNames")
    return (c.like(c.codes, cats),)


def _reordercats(args, *, nargout=1):
    c = _need(args, "reordercats")
    cats = _cat_list(args[1], "reordercats") if len(args) > 1 else sorted(c.cats)
    if sorted(cats) != sorted(c.cats):
        raise _err("NEWORDER must be a permutation of the categories.", "MATLAB:categorical:reordercats:InvalidNeworder")
    return (c.like(_remap(c.codes, c.cats, cats), cats),)


def _setcats(args, *, nargout=1):
    c = _need(args, "setcats", 2)
    cats = _cat_list(args[1], "setcats")
    return (c.like(_remap(c.codes, c.cats, cats), cats),)


def _isundefined(args, *, nargout=1):
    v = args[0] if args else None
    if not isinstance(v, CategoricalValue):
        cls = v.matlab_class() if v is not None else "double"
        raise _err(f"Undefined function 'isundefined' for input arguments of type '{cls}'.", "MATLAB:UndefinedFunction")
    return (_bool(v.codes == 0),)


def _iscategorical(args, *, nargout=1):
    return (_bool(isinstance(args[0], CategoricalValue)),)


def _isordinal(args, *, nargout=1):
    return (_bool(isinstance(args[0], CategoricalValue) and args[0].ordinal),)


def _isprotected(args, *, nargout=1):
    return (_bool(isinstance(args[0], CategoricalValue) and args[0].protected),)


def _iscategory(args, *, nargout=1):
    c = _need(args, "iscategory", 2)
    t = _cat_list(args[1], "iscategory")
    shape = (1, 1) if is_text(args[1]) else tuple(args[1].shape)
    return (_bool(np.array([s in c.cats for s in t]).reshape(shape, order="F")),)


def _labels_cell(c):
    from openmatlab.runtime.cell_value import CellValue

    labs = np.array(c.labels(), dtype=object).reshape(c.shape, order="F")
    return CellValue(rows=tuple(tuple(_cv(s) for s in row) for row in labs))


def _wrap(name, orig):
    def f(args, *, nargout=1):
        if args and isinstance(args[0], CategoricalValue):
            c = args[0]
            if name in ("double", "single", "int8", "int16", "int32", "int64", "uint8", "uint16", "uint32", "uint64"):
                if name in ("double", "single"):
                    a = np.where(c.codes == 0, np.nan, c.codes.astype(float))
                    return orig([_num(a)], nargout=1)
                return orig([_num(c.codes.astype(float))], nargout=1)
            if name == "char":
                labs = c.labels()
                w = max((len(s) for s in labs), default=0)
                return (_cv("\n".join(s.ljust(w) for s in labs)) if len(labs) > 1 else _cv(labs[0] if labs else ""),)
            if name == "cellstr":
                return (_labels_cell(c),)
            if name == "string":
                from openmatlab.runtime import string_array as sa

                labs = np.array([None if s == UNDEF else s for s in c.labels()], dtype=object)
                return (sa.make(labs.reshape(c.shape, order="F")),)
            if name in ("numel", "length", "isempty", "size", "ndims", "isrow", "iscolumn", "isvector", "isscalar"):
                return orig([NDArrayValue(np.zeros(c.shape))] + list(args[1:]), nargout=nargout)
            if name == "disp":
                import sys

                sys.stdout.write(c.body_text() if c.numel() > 1 else c.display_text() + "\n")
                return ()
            if name == "summary":
                import sys

                lines = [f"     {s}      {int(np.sum(c.codes == i + 1))} " for i, s in enumerate(c.cats)]
                if np.any(c.codes == 0):
                    lines.append(f"     {UNDEF}      {int(np.sum(c.codes == 0))} ")
                sys.stdout.write("\n".join(lines) + "\n")
                return ()
            if name == "unique":
                used = sorted(set(int(x) for x in c.codes.reshape(-1) if x))
                out = np.array(used, dtype=np.int64)
                return (c.like(out.reshape(-1, 1) if c.shape[0] != 1 or c.shape[1] == 1 else out.reshape(1, -1)),)
        return orig(args, nargout=nargout)

    return f


def _no_summary(args, *, nargout=1):
    cls = args[0].matlab_class() if args else "double"
    raise _err(f"Undefined function 'summary' for input arguments of type '{cls}'.", "MATLAB:UndefinedFunction")


def register(builtins) -> None:
    builtins.setdefault("summary", _no_summary)
    builtins.update(categorical=_categorical, categories=_categories, countcats=_countcats, addcats=_addcats,
                    removecats=_removecats, mergecats=_mergecats, renamecats=_renamecats, reordercats=_reordercats,
                    setcats=_setcats, isundefined=_isundefined, iscategorical=_iscategorical, isordinal=_isordinal,
                    isprotected=_isprotected, iscategory=_iscategory)
    for n in ("double", "single", "int8", "int16", "int32", "int64", "uint8", "uint16", "uint32", "uint64", "char",
              "cellstr", "string", "numel", "length", "isempty", "size", "ndims", "isrow", "iscolumn", "isvector",
              "isscalar", "disp", "summary", "unique"):
        if n in builtins:
            builtins[n] = _wrap(n, builtins[n])
