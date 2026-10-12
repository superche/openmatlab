# OpenMATLAB classic showcase

Minimal `.m` scripts for **one** screen-recording of classic MATLAB-style features.

| File | Shows |
|------|--------|
| `01_matrix.m` | Matrix create, `*`, `.*`, `^`, `size`, `sum` |
| `02_linspace_plot.m` | `linspace`, `plot`, `show` |
| `03_control.m` | `for` / `while` / `if` / `switch` |
| `04_cells_unique.m` | cell, `unique`, `find`, `sort` descend |
| `run_all.sh` | Runs each via `openmatlab` with separators |

## Smoke (headless Agg)

```bash
cd /workspace/openmatlab
. .venv/bin/activate
unset OPENMATLAB_PLOT_INTERACTIVE
export MPLBACKEND=Agg
bash demos/showcase/run_all.sh | tee demos/showcase/smoke_log.txt
```

## Live recording (one sequence)

```bash
cd /workspace/openmatlab
. .venv/bin/activate
export OPENMATLAB_PLOT_INTERACTIVE=1
bash demos/showcase/run_all.sh
```

Prefer typing the short per-demo commands (see agent report) so the plot window is visible between steps.
