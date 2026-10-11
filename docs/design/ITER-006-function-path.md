# ITER-006 Design: ToolboxPath + FunctionResolver (slice 1)

**Issue:** #6

## This PR slice (KISS)

1. `ToolboxPath.find_mfile(name)` searches `entries` for `name.m` / `name.M`
2. `FunctionResolver.which` / `resolve` consult path after builtins
3. `resolve` on path hit raises clear `NotImplementedError` until .m eval exists
   — **path discovery works**; loading deferred

## Later slice

Parse `function` files (#3 grammar extension) + call frames.
