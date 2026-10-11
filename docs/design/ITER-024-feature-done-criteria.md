# Feature `done` criteria — Epic #2 / Issue #24

Per PROCESS § Feature status criteria. Promote only when all bullets hold.
Non-goals listed do **not** block `done`.

## numerics.array_value → done
- Observable: scalar 1×1 `NDArrayValue`; `matlab_class` / shape / `is_scalar`
- Tests: `tests/unit/test_numpy_backend.py`
- Non-goals: sparse, gpu

## numerics.numpy_backend → done
- Observable: literal, matmul, elem ops, index, colon, transpose via backend
- Tests: `tests/unit/test_numpy_backend.py`, BDD array
- Non-goals: complex dtype suite, sparse, LAPACK wrappers beyond what matmul needs

## lang.lexer → done (matrix+control MVP)
- Observable: matrix tokens, STRING, KW_FUNCTION/IF/ELSE/ELSEIF/FOR/END, relational
- Tests: lexer + control_flow + addpath string tests
- Non-goals: cells, single-quoted strings, while

## lang.parser → done (same MVP)
- Observable: matrix/index/colon/transpose/function/MultiAssign/If/For
- Tests: parser_matrix, multi_assign, control_flow
- Non-goals: while/switch/try, full MATLAB precedence edge cases

## lang.matrix_literal → done
- Parsed + evaluated to Array
- Tests: parser_matrix + evaluator
- Non-goals: nested non-scalar cells in `[ ]`

## lang.elementwise_ops → done
- `.* ./ .^` vs `*` evaluated
- Tests: parser + evaluator BDD
- Non-goals: `.\` left divide

## lang.indexing_colon → done
- `A(i,j)` and `a:b` / `a:s:b` evaluated
- Tests: parser_matrix + evaluator
- Non-goals: `end` as index, logical indexing

## lang.function_def → done (file-level)
- `function … end` parse + `.m` load
- Tests: mfile_functions
- Non-goals: nested functions, nargin/nargout specials

## runtime.evaluator → done (MVP workbench)
- Matrix eval, path `.m`, multi-assign, if/for, path builtins, plot/show
- Tests: evaluator, multi_assign, control_flow, addpath, plot
- Non-goals: while, classes, scripts without function

## host.display_policy → done
- `;` suppress, ans, pretty-print Array/CharValue
- Tests: evaluator + display paths
- Non-goals: format short/long eng, HTML

## host.repl → done
- `run_line`, bare CLI REPL entry
- Tests: evaluator/repl usage across suite
- Non-goals: readline completion history persistence

## runtime.session → done
- `create_default` wires numerics/display/plots/path; interactive policy
- Tests: architecture + interactive_plot + evaluator
- Non-goals: multi-session manager

## graphics.matplotlib → done (Agg+policy)
- Agg default; interactive flag; plot xy; show policy
- Tests: test_plot + test_interactive_plot
- Non-goals: 3D, imagesc, GUI toolkit matrix

## graphics.plot_mvp → done
- Builtin `plot` / `show` / `drawnow`
- Tests: plot + interactive_plot
- Non-goals: plotyy, hold on full semantics

## host.plot_surface → done
- plot/close/show façade
- Tests: plot + interactive_plot
- Non-goals: multiple surfaces per session

## libs.toolbox_path → done
- addpath/rmpath/find_mfile + language addpath
- Tests: toolbox_path + addpath_which
- Non-goals: genpath, pathsep persistence file

## libs.mfile_loading → done
- parse_mfile + MFileCallable
- Tests: mfile_functions
- Non-goals: nested, classdef, p-code

## runtime.function_resolver → done
- builtins → path → cache load; which
- Tests: toolbox_path + mfile + addpath
- Non-goals: private/ folders, package +name

## Remain `partial` (explicit blockers)
- `lang.tokens_reserved` / `lang.ast_matrix_forms` — already `done`
- Future: while, single-quote char, cells — no feature_id flip without new Issue
