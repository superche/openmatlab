# Epic #692 (T-E2): categorical

Milestone: [M10 Tables and data types](../milestones/M10-tables.md), criterion T04.

## Design

- **Storage.** `CategoricalValue` (`runtime/categorical_value.py`) holds a 2-D integer code array (0 = `<undefined>`, k = the k-th category), the ordered category names, and the `Ordinal`/`Protected` flags (ordinal implies protected). It is a value type and follows the `objects.py` protocol (`index`, `assign`, `binop`, `display_text`), so tables hold it as an ordinary variable with no table-specific code.
- **Construction** (`libs/categorical_builtins.py`). `categorical(data)` takes cellstr, string, char, numeric or logical data. Without a valueset the categories are the sorted unique non-missing values. `''`, `<missing>` and `NaN` become undefined. With `valueset`, values outside it become undefined. `catnames` renames the categories and may repeat a name to merge values. `'Ordinal'` and `'Protected'` are accepted.
- **Methods.** `categories`, `countcats` (along the first non-singleton dimension, or the `dim` argument), `addcats` (with `'Before'`/`'After'`; ordinal arrays require one of them), `removecats` (with no list, removes unused categories), `mergecats` (ordinal arrays require consecutive categories), `renamecats`, `reordercats`, `setcats`, `isundefined`, `iscategorical`, `isordinal`, `isprotected`, `iscategory`, `summary`, `unique`. `double`/`single` return codes with NaN for undefined; integer classes return codes. `char`, `cellstr` and `string` return labels. `size`, `numel` and related functions see the code shape.
- **Operators.** `==` and `~=` work against categorical values, text and cellstr; undefined never compares equal. `<`, `>`, `<=` and `>=` are allowed only for ordinal arrays with the same categories, and otherwise raise `MATLAB:categorical:NotOrdinal`. Other operators are errors.
- **Indexing and assignment.** Linear and 2-D indexing, `end`, `:` and logical masks all work. Assigning a new label adds a category, unless the array is protected (`MATLAB:categorical:ProtectedForAssign`). `c(i) = []` deletes elements.
- **Evaluator seams.** These are small and generic. Transposing calls `transpose_value` when the operand defines it. `[...]` with any categorical element builds the union of categories in order of appearance. Object indexing (`obj(args)` / `obj(args) = v`) now resolves `end` and a bare `:` against the object's shape (`_object_index_args`). This also fixes `d(end)` for datetime/duration; `containers.Map` keys are left untouched.

## Adversarial review

- **Probe sweep:** bad data or valueset types, mismatched catnames, an out-of-range index, an unknown category in merge, a duplicate category in `addcats`, arithmetic, and relational comparison on a non-ordinal array all raise MATLAB errors with no traceback (`tests/unit/test_categorical.py::test_errors_are_matlab_errors`).
- **No existing test was changed;** the full unit, bdd and conformance suite is green.
- **Deferred (residual #717):** N-D categorical, the scalar display header, a logical valueset, protected concatenation rules, and the `summary` layout. `sort` and `ismember` belong to T05 (#693).
