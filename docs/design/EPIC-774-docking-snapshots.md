# Epic #774 (M13 G-E7): Workbench figure docking + image snapshot infrastructure

Milestone: [M13 Graphics completion](../milestones/M13-graphics.md), criteria G09 (second half) and G10.

## Problem

G09's output-routing half was delivered by #767. Docking and focus were missing: `WindowStyle` was stored but the Workbench Figures panel did not treat docked figures specially, and a new figure did not take focus through the host. G10 needed ≥ 40 golden snapshot scenes with deterministic rendering and a tolerance comparator; no snapshot module existed.

## Design

### G09 — docking and focus

- `FigureInfo` carries `number`, `docked` (`WindowStyle == 'docked'`) and `visible`.
- `FigureManager.list` / `docked` / `focused` / `set_docked` / `focus` sync with the handle model. Focusing a figure sets `current_figure` (gcf). A new `figure` becomes focused.
- `DefaultFigureWindowStyle` (and other `Default<Type><Prop>` on root/figure/axes) lives in `libs/graphics_defaults.py`: nearest ancestor wins; creating-function explicit values are kept; axes titles/labels ignore `DefaultText*`.
- The tk Figures panel lists every open figure and marks docked ones with `[docked]`. Selecting Focus raises that figure; docked figures are the ones shown in the panel (MATLAB desktop Figures window).

### G10 — golden snapshots

New module `openmatlab.qa.snapshots`:

- **Scenes.** ≥ 40 named scenes (2-D charts, layout, 3-D, colour/image, annotations). Each scene is a short `.m` fragment run with `Visible` off.
- **Determinism.** Backend pinned to `Agg`; `rcParams` fix font family (`DejaVu Sans`), font size, DPI (100), figure size, and antialiasing off for lines where supported. `HASHLIB` digest of the rendered PNG bytes is the scene digest.
- **Goldens.** Our own renders under `tests/conformance/golden/snapshots/<name>.png`, committed with the module. Never MathWorks screenshots.
- **Comparator.** A scene passes if ≤ 1 % of pixels have CIE76 ΔE > 10 **or** SSIM ≥ 0.98 (NumPy-only Lab and SSIM). `check_all(tmp)` writes renders under `tmp` and returns `Result(name, ok, digest)` per scene. Re-running yields the same digests.

### G09 / G10 conformance

`m13_g09_workbench_figures.py` already asserts docked + focus. `m13_g10_snapshots.py` asserts ≥ 40 scenes, all within tolerance, and digest stability. Manifest flips both to `met`.

## Adversarial review

| Attack | Result |
|---|---|
| `figure('WindowStyle','docked')` then `figure` | First docked, second focused and undocked (unit test) |
| `set(groot,'DefaultFigureWindowStyle','docked')` | New figures dock (unit test) |
| Focus via FigureManager | `gcf` Number matches (unit test) |
| Invalid `DefaultLineBogus` / negative LineWidth | MATLAB identifiers (unit test) |
| Nearest-ancestor default vs title FontSize | Ancestor wins; titles ignore DefaultText* (unit test) |
| Snapshot re-run | Digests identical (conformance z3) |
| Goldens missing or corrupted | Comparator fails that scene; others still checked |
| Existing tests | Unchanged in this epic |

## Non-goals

Pixel parity with MATLAB; interactive dock/undock drag; `uifigure`; animation frames.
