# Feature map (human index) — QA layer 1

**Source of truth:** [`feature_map.yaml`](feature_map.yaml)

Dump: `openmatlab features`  
Full QA system: [`QA.md`](QA.md) (five layers)  
Cases: [`TEST_CATALOG.md`](TEST_CATALOG.md) · Defects: GitHub Issues ([`WORKFLOW.md`](WORKFLOW.md))

## How to update

1. Edit `feature_map.yaml` (stable `id`, `layer`, `status`).
2. Optionally link `cases: [tc.…]` into the test catalog.
3. Run `openmatlab features` and `openmatlab test --suite unit`.

## By layer (intent)

| Layer | Focus now | Next fill |
|-------|-----------|-----------|
| host | CLI QA contracts, DisplayPolicy/PlotSurface stubs | real display + REPL |
| lang | reserved TokenType + AST | lexer/parser matrix subset |
| runtime | Workspace/Session partial; Value/Array protocols | concrete Array + Evaluator |
| numerics | ArrayBackend stub | NumPyArrayBackend + Array |
| graphics | GraphicsBackend stub | Matplotlib plot MVP |
| libs | ToolboxPath list ops | find_mfile + .m load |
| qa | five-layer system; Issues+pytest+gh | denser conformance cases |
