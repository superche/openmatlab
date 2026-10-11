# Option A — Entry-point discovery (`importlib.metadata`)

Plugins declare contributions in packaging metadata
(`project.entry-points` / `importlib.metadata.entry_points`).
Host loads groups like `openmatlab.domain` and `openmatlab.ui`.

This demo **stubs** the registry in-process (no real install) so it runs
without building wheels — same call shape as production entry points.
