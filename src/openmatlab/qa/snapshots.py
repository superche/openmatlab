"""Golden image snapshots (M13 G10, Epic #774).

Renders ≥ 40 named scenes with a pinned Matplotlib Agg backend (font, DPI, size)
and compares each against our own committed PNG under
``tests/conformance/golden/snapshots/``. A scene passes when ≤ 1 % of pixels have
CIE76 ΔE > 10 **or** SSIM ≥ 0.98. Digests are SHA-256 of the rendered PNG bytes.
"""

from __future__ import annotations

import hashlib
import io
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import numpy as np

_REPO = Path(__file__).resolve().parents[3]
GOLDEN_DIR = _REPO / "tests" / "conformance" / "golden" / "snapshots"

DPI = 100
FIGSIZE = (4.0, 3.0)
DELTA_E_MAX = 10.0
DELTA_E_FRAC = 0.01
SSIM_MIN = 0.98


@dataclass(frozen=True)
class Scene:
    name: str
    code: str


@dataclass(frozen=True)
class Result:
    name: str
    ok: bool
    digest: str
    detail: str = ""


def _pin_matplotlib() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib as mpl

    mpl.rcParams.update({
        "backend": "Agg",
        "figure.dpi": DPI,
        "savefig.dpi": DPI,
        "figure.figsize": list(FIGSIZE),
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "axes.unicode_minus": False,
        "path.simplify": False,
        "agg.path.chunksize": 0,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.bbox": None,
        "savefig.pad_inches": 0.1,
    })


def scenes() -> List[Scene]:
    """≥ 40 golden snapshot scenes (own renders; never MathWorks screenshots)."""
    s = [
        Scene("plot_line", "figure('Visible','off'); plot(1:10); title('line');"),
        Scene("plot_linespec", "figure('Visible','off'); plot(1:5, (1:5).^2, 'ro-');"),
        Scene("plot_multi", "figure('Visible','off'); plot(1:8, [1:8; (1:8).^0.5]');"),
        Scene("scatter", "figure('Visible','off'); scatter(1:20, sin(1:20), 36, 1:20);"),
        Scene("bar", "figure('Visible','off'); bar([1 3 2 5 4]);"),
        Scene("barh", "figure('Visible','off'); barh([2 4 1 3]);"),
        Scene("bar_stacked", "figure('Visible','off'); bar([1 2; 3 1; 2 4], 'stacked');"),
        Scene("stem", "figure('Visible','off'); stem(1:8, cos(1:8));"),
        Scene("stairs", "figure('Visible','off'); stairs(1:10, sin(1:10));"),
        Scene("area", "figure('Visible','off'); area(1:6, [1 2 3 2 1 2]);"),
        Scene("errorbar", "figure('Visible','off'); errorbar(1:5, [1 3 2 4 3], 0.3*ones(1,5));"),
        Scene("pie", "figure('Visible','off'); pie([2 3 5 1]);"),
        Scene("histogram", "figure('Visible','off'); histogram(randn(200,1), 12);"),
        Scene("fill", "figure('Visible','off'); fill([0 1 1 0], [0 0 1 1], [0.7 0.8 1]);"),
        Scene("patch", "figure('Visible','off'); patch([0 1 0.5], [0 0 1], [1 0.6 0.4]);"),
        Scene("line_primitive", "figure('Visible','off'); line([0 1 2], [0 1 0]); box on;"),
        Scene("loglog", "figure('Visible','off'); loglog(logspace(0,2,20), logspace(0,2,20).^1.5);"),
        Scene("semilogx", "figure('Visible','off'); semilogx(logspace(0,2,30), sin(logspace(0,2,30)));"),
        Scene("semilogy", "figure('Visible','off'); semilogy(1:20, exp(0.2*(1:20)));"),
        Scene("hold_multi", "figure('Visible','off'); plot(1:10); hold on; plot(1:10, (1:10)/2, '--'); hold off;"),
        Scene("subplot_2x2", "figure('Visible','off'); for k=1:4, subplot(2,2,k); plot(1:k+2); end"),
        Scene("subplot_rows", "figure('Visible','off'); subplot(2,1,1); plot(1:5); subplot(2,1,2); bar(1:5);"),
        Scene("tiledlayout", "figure('Visible','off'); tiledlayout(1,2); nexttile; plot(1:6); nexttile; stem(1:6);"),
        Scene("yyaxis", "figure('Visible','off'); yyaxis left; plot(1:5); yyaxis right; plot([10 20 15 25 20]);"),
        Scene("imagesc", "figure('Visible','off'); imagesc(magic(8)); axis image; colorbar;"),
        Scene("image", "figure('Visible','off'); image(reshape(1:64,8,8)); axis image;"),
        Scene("colormap_jet", "figure('Visible','off'); imagesc(peaks(24)); colormap(jet); colorbar;"),
        Scene("colormap_hot", "figure('Visible','off'); imagesc(peaks(24)); colormap(hot); colorbar;"),
        Scene("contour", "figure('Visible','off'); contour(peaks(30), 8);"),
        Scene("contourf", "figure('Visible','off'); contourf(peaks(30), 10); colorbar;"),
        Scene("surf", "figure('Visible','off'); surf(peaks(20));"),
        Scene("mesh", "figure('Visible','off'); mesh(peaks(20));"),
        Scene("plot3", "figure('Visible','off'); t=linspace(0,4*pi,80); plot3(sin(t),cos(t),t);"),
        Scene("scatter3", "figure('Visible','off'); scatter3(randn(40,1),randn(40,1),randn(40,1),25);"),
        Scene("view_3d", "figure('Visible','off'); surf(peaks(16)); view(45,30);"),
        Scene("text_title", "figure('Visible','off'); plot(1:5); title('Title'); xlabel('x'); ylabel('y');"),
        Scene("legend", "figure('Visible','off'); plot(1:5); hold on; plot(1:5,5:-1:1); legend('a','b');"),
        Scene("annotation_arrow", "figure('Visible','off'); plot(1:3); annotation('arrow',[0.2 0.5],[0.2 0.6]);"),
        Scene("grid_box", "figure('Visible','off'); plot(sin(linspace(0,2*pi,50))); grid on; box on;"),
        Scene("axis_equal", "figure('Visible','off'); plot(cos(linspace(0,2*pi,60)),sin(linspace(0,2*pi,60))); axis equal;"),
        Scene("xlim_ylim", "figure('Visible','off'); plot(1:20); xlim([5 15]); ylim([-1 25]);"),
        Scene("colorbar_clim", "figure('Visible','off'); imagesc(peaks(20)); clim([-4 4]); colorbar;"),
        Scene("stairs_hold", "figure('Visible','off'); stairs(1:6); hold on; stairs(1:6,(1:6)+1); hold off;"),
        Scene("bar_grouped", "figure('Visible','off'); bar([1 2 3; 2 1 4; 3 3 2]);"),
        Scene("histogram_bins", "figure('Visible','off'); histogram(rand(300,1), 0:0.1:1);"),
        Scene("patch_alpha", "figure('Visible','off'); patch([0 1 1 0],[0 0 1 1],[0.2 0.6 0.9],'FaceAlpha',0.5);"),
    ]
    assert len(s) >= 40
    return s


def _rgb_from_png_bytes(data: bytes) -> np.ndarray:
    from matplotlib import image as mpimg

    arr = mpimg.imread(io.BytesIO(data), format="png")
    if arr.ndim == 2:
        arr = np.stack([arr, arr, arr], axis=-1)
    if arr.shape[-1] == 4:
        arr = arr[..., :3]
    return np.asarray(arr, dtype=np.float64)


def _png_bytes_from_figure(m, fig) -> bytes:
    from openmatlab.libs import figio

    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        figio.render_to_file(m, fig, path, "png", float(DPI), background="white", crop_axes=False)
        return Path(path).read_bytes()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def render_scene(scene: Scene) -> Tuple[bytes, str]:
    """Run ``scene.code``, render gcf to PNG bytes; return (bytes, sha256 hex)."""
    _pin_matplotlib()
    # Seed RNG so randn/rand scenes are deterministic across runs
    np.random.seed(774)
    from openmatlab.host.repl import ReplSession

    s = ReplSession()
    s.run_line("rng(774); close all;")
    try:
        s.run_line("rng(774);")
    except Exception:
        pass
    s.run_line(scene.code)
    m = getattr(s.session.plots, "_gmodel", None)
    if m is None:
        raise RuntimeError(f"snapshots: no graphics model after scene {scene.name}")
    f = m.current_figure
    if f is None or not f.alive:
        figs = m.figures()
        if not figs:
            raise RuntimeError(f"snapshots: scene {scene.name} left no figure open")
        f = figs[-1]
    data = _png_bytes_from_figure(m, f)
    s.run_line("close all;")
    return data, hashlib.sha256(data).hexdigest()


def _rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    r = np.clip(rgb, 0.0, 1.0)
    a = np.where(r <= 0.04045, r / 12.92, ((r + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124564, 0.3575761, 0.1804375],
                  [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]])
    xyz = a @ m.T
    w = np.array([0.95047, 1.0, 1.08883])
    t = xyz / w
    f = np.where(t > (6 / 29) ** 3, np.cbrt(t), t * (29 / 6) ** 2 / 3 + 4 / 29)
    L = 116 * f[..., 1] - 16
    A = 500 * (f[..., 0] - f[..., 1])
    B = 200 * (f[..., 1] - f[..., 2])
    return np.stack([L, A, B], axis=-1)


def delta_e_frac(a: np.ndarray, b: np.ndarray) -> float:
    h, w = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
    if h == 0 or w == 0:
        return 1.0
    la, lb = _rgb_to_lab(a[:h, :w]), _rgb_to_lab(b[:h, :w])
    de = np.sqrt(np.sum((la - lb) ** 2, axis=-1))
    return float(np.mean(de > DELTA_E_MAX))


def ssim(a: np.ndarray, b: np.ndarray) -> float:
    h, w = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
    if h < 2 or w < 2:
        return 0.0
    x, y = a[:h, :w].astype(np.float64), b[:h, :w].astype(np.float64)
    C1, C2 = 0.01 ** 2, 0.03 ** 2
    scores = []
    for c in range(x.shape[-1]):
        xc, yc = x[..., c], y[..., c]
        mx, my = xc.mean(), yc.mean()
        vx, vy = xc.var(), yc.var()
        vxy = ((xc - mx) * (yc - my)).mean()
        scores.append(((2 * mx * my + C1) * (2 * vxy + C2)) /
                      ((mx ** 2 + my ** 2 + C1) * (vx + vy + C2) + 1e-12))
    return float(np.mean(scores))


def within_tolerance(got: np.ndarray, want: np.ndarray) -> Tuple[bool, str]:
    frac, s = delta_e_frac(got, want), ssim(got, want)
    return frac <= DELTA_E_FRAC or s >= SSIM_MIN, f"deltaE_frac={frac:.4f} ssim={s:.4f}"


def golden_path(name: str) -> Path:
    return GOLDEN_DIR / f"{name}.png"


def check_scene(scene: Scene, out_dir: Optional[Path] = None) -> Result:
    data, digest = render_scene(scene)
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{scene.name}.png").write_bytes(data)
    gp = golden_path(scene.name)
    if not gp.is_file():
        return Result(scene.name, False, digest, "missing golden")
    ok, detail = within_tolerance(_rgb_from_png_bytes(data), _rgb_from_png_bytes(gp.read_bytes()))
    return Result(scene.name, ok, digest, detail)


def check_all(out_dir: Optional[Path] = None) -> List[Result]:
    return [check_scene(sc, out_dir) for sc in scenes()]


def write_goldens(only: Optional[Sequence[str]] = None) -> List[Path]:
    """Render and overwrite committed goldens (maintenance helper)."""
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for sc in scenes():
        if only is not None and sc.name not in only:
            continue
        data, _ = render_scene(sc)
        p = golden_path(sc.name)
        p.write_bytes(data)
        written.append(p)
    return written
