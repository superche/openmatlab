"""Global ``imbinarize`` and ``bwareaopen`` for one 2-D FOV (M16 I-E2, Epic #1021).

Default ``imbinarize(I)`` is Otsu's global threshold, the same call as
``imbinarize(I, graythresh(I))``. An RGB image is reduced with the published
``rgb2gray`` weights 0.2989, 0.5870, and 0.1140, rounded back to the integer
class when the input is uint8 or uint16. Foreground is ``im2double(gray) > level``.

``bwareaopen(BW, P)`` drops 2-D connected components whose area is strictly
less than ``P``. The default connectivity is 8. ``conn`` may be 4 or 8.
Labeling stays inside this module. ``bwlabel``, ``bwconncomp``, and
``regionprops`` are not registered here (I-E3, Epic #1022).

``'adaptive'``, a threshold matrix, 3-D images, and connectivity matrices are
rejected. This is not a copy of the Octave image package.
"""

from __future__ import annotations

import numpy as np

# Published rgb2gray luminance weights (MATLAB documentation).
RGB_WEIGHTS = (0.2989, 0.5870, 0.1140)


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _text(v):
    from openmatlab.runtime.char_value import CharValue

    if isinstance(v, CharValue):
        return v.text
    if getattr(v, "is_string", False) and v.numel() == 1:
        return str(v.data.flat[0])
    return None


def _array(v, fn: str) -> np.ndarray:
    if _text(v) is not None or not hasattr(v, "backend_buffer"):
        raise _err(f"{fn}: expected a numeric or logical array", "MATLAB:invalidType")
    return np.asarray(v.backend_buffer())


def _scalar(v, fn: str) -> float:
    arr = _array(v, fn)
    if arr.size != 1:
        raise _err(f"{fn}: expected a scalar", "MATLAB:invalidType")
    value = float(arr.reshape(-1)[0])
    if not np.isfinite(value):
        raise _err(f"{fn}: expected a finite scalar", "MATLAB:invalidType")
    return value


def _as_gray(data: np.ndarray) -> np.ndarray:
    """2-D luminance in the input class. RGB uses the documented weights."""
    arr = np.asarray(data)
    if arr.ndim == 3:
        if arr.shape[2] != 3:
            raise _err("imbinarize: expected a 2-D image or an RGB image", "OpenMATLAB:imbinarize:BadImage")
        channels = [arr[..., i].astype(np.float64) for i in range(3)]
        acc = RGB_WEIGHTS[0] * channels[0] + RGB_WEIGHTS[1] * channels[1] + RGB_WEIGHTS[2] * channels[2]
        if arr.dtype == np.uint8:
            return np.clip(np.rint(acc), 0, 255).astype(np.uint8)
        if arr.dtype == np.uint16:
            return np.clip(np.rint(acc), 0, 65535).astype(np.uint16)
        return acc
    if arr.ndim != 2:
        raise _err("imbinarize: expected a 2-D image or an RGB image", "OpenMATLAB:imbinarize:BadImage")
    return arr


def _im2double(gray: np.ndarray) -> np.ndarray:
    if gray.dtype == np.uint8:
        return gray.astype(np.float64) / 255.0
    if gray.dtype == np.uint16:
        return gray.astype(np.float64) / 65535.0
    if gray.dtype == np.bool_ or np.issubdtype(gray.dtype, np.bool_):
        return gray.astype(np.float64)
    return np.asarray(gray, dtype=np.float64)


def _histogram_u8(gray: np.ndarray) -> np.ndarray:
    """256 bins over the class range. Float images are clipped to [0, 1]."""
    if gray.dtype == np.uint8:
        sample = gray
    elif gray.dtype == np.uint16:
        sample = np.clip(np.rint(gray.astype(np.float64) * (255.0 / 65535.0)), 0, 255).astype(np.uint8)
    else:
        unit = np.clip(np.asarray(gray, dtype=np.float64), 0.0, 1.0)
        sample = np.clip(np.rint(unit * 255.0), 0, 255).astype(np.uint8)
    return np.bincount(sample.reshape(-1), minlength=256).astype(np.float64)


def otsu_level(gray: np.ndarray) -> float:
    """Normalized Otsu level ``t/255``.

    Bin ``t`` is the last intensity in the dark class (0..t). The bright class
    is ``t+1``..255. The level maximizes between-class variance. Ties take the
    smallest ``t``. A constant image has variance 0 for every split, so ``t`` is 0.
    """
    hist = _histogram_u8(gray)
    total = float(hist.sum())
    if total == 0.0:
        return 0.0
    index = np.arange(256, dtype=np.float64)
    omega = np.cumsum(hist) / total
    mu = np.cumsum(hist * index) / total
    mu_t = float(mu[-1])
    denom = omega * (1.0 - omega)
    sigma = np.zeros(256, dtype=np.float64)
    ok = denom > 0.0
    sigma[ok] = (mu_t * omega[ok] - mu[ok]) ** 2 / denom[ok]
    return float(int(np.argmax(sigma)) / 255.0)


def binarize(data: np.ndarray, level: float) -> np.ndarray:
    if not 0.0 <= level <= 1.0:
        raise _err("imbinarize: threshold must be in [0, 1]", "OpenMATLAB:imbinarize:ThresholdRange")
    gray = _as_gray(data)
    return _im2double(gray) > level


def component_areas(mask: np.ndarray, conn: int = 8) -> np.ndarray:
    """Area of each foreground component, 4- or 8-connected. Not a builtin."""
    labels, roots = _label(mask, conn)
    if labels.size == 0 or int(labels.max()) == 0:
        return np.zeros(0, dtype=np.int64)
    counts = np.bincount(roots[labels[mask]].reshape(-1))
    return counts[counts > 0]


def area_open(mask: np.ndarray, min_area: float, conn: int = 8) -> np.ndarray:
    """Keep foreground components whose area is greater than or equal to ``min_area``."""
    labels, roots = _label(mask, conn)
    out = np.zeros(mask.shape, dtype=bool)
    if labels.size == 0 or int(labels.max()) == 0:
        return out
    counts = np.bincount(roots[labels[mask]].reshape(-1))
    keep = counts >= min_area
    keep[0] = False
    out[mask] = keep[roots[labels[mask]]]
    return out


def _label(mask: np.ndarray, conn: int):
    fg = np.asarray(mask, dtype=bool)
    if fg.ndim != 2:
        raise _err("bwareaopen: only 2-D images are supported", "OpenMATLAB:bwareaopen:Dimension")
    height, width = fg.shape
    labels = np.zeros((height, width), dtype=np.int32)
    parent = [0]

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(left: int, right: int) -> None:
        a, b = find(left), find(right)
        if a != b:
            parent[b] = a

    offsets = ((0, -1), (-1, 0)) if conn == 4 else ((0, -1), (-1, -1), (-1, 0), (-1, 1))
    nid = 0
    for row in range(height):
        for col in range(width):
            if not fg[row, col]:
                continue
            neighbors = []
            for dr, dc in offsets:
                rr, cc = row + dr, col + dc
                if rr < 0 or cc < 0 or cc >= width:
                    continue
                lab = int(labels[rr, cc])
                if lab:
                    neighbors.append(lab)
            if not neighbors:
                nid += 1
                parent.append(nid)
                labels[row, col] = nid
            else:
                best = min(neighbors)
                labels[row, col] = best
                for lab in neighbors:
                    union(best, lab)
    roots = np.fromiter((find(i) for i in range(nid + 1)), dtype=np.int32, count=nid + 1)
    return labels, roots


def _logical(mask: np.ndarray):
    from openmatlab.numerics.ndarray_value import NDArrayValue

    return NDArrayValue(np.asarray(mask, dtype=bool))


def _graythresh(args, *, nargout=1):
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    if len(args) != 1:
        raise _err("Too many input arguments.", "MATLAB:TooManyInputs")
    from openmatlab.numerics.ndarray_value import NDArrayValue

    level = otsu_level(_as_gray(_array(args[0], "graythresh")))
    return (NDArrayValue(np.array([[level]], dtype=np.float64)),)


def _imbinarize(args, *, nargout=1):
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    if len(args) > 2:
        raise _err("Too many input arguments.", "MATLAB:TooManyInputs")
    image = _array(args[0], "imbinarize")
    level = None
    if len(args) == 2:
        word = _text(args[1])
        if word is not None:
            key = word.strip().lower()
            if key == "adaptive":
                raise _err(
                    "imbinarize: adaptive threshold is not supported",
                    "OpenMATLAB:imbinarize:Adaptive",
                )
            if key != "global":
                raise _err(f"imbinarize: unknown method '{word}'", "OpenMATLAB:imbinarize:BadMethod")
        else:
            arr = _array(args[1], "imbinarize")
            if arr.size != 1:
                raise _err(
                    "imbinarize: a threshold matrix is not supported",
                    "OpenMATLAB:imbinarize:ThresholdMatrix",
                )
            level = float(arr.reshape(-1)[0])
            if not np.isfinite(level):
                raise _err("imbinarize: threshold must be in [0, 1]", "OpenMATLAB:imbinarize:ThresholdRange")
    if level is None:
        level = otsu_level(_as_gray(image))
    return (_logical(binarize(image, level)),)


def _bwareaopen(args, *, nargout=1):
    if len(args) < 2:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    if len(args) > 3:
        raise _err("Too many input arguments.", "MATLAB:TooManyInputs")
    bw = _array(args[0], "bwareaopen")
    if bw.ndim != 2:
        raise _err("bwareaopen: only 2-D images are supported", "OpenMATLAB:bwareaopen:Dimension")
    if np.issubdtype(bw.dtype, np.floating) and np.any(~np.isfinite(bw)):
        raise _err("bwareaopen: image must be finite", "OpenMATLAB:bwareaopen:BadImage")
    min_area = _scalar(args[1], "bwareaopen")
    if min_area < 0.0:
        raise _err("bwareaopen: P must be nonnegative", "OpenMATLAB:bwareaopen:BadArea")
    conn = 8
    if len(args) == 3:
        word = _text(args[2])
        arr = None if word is not None else _array(args[2], "bwareaopen")
        if word is not None or arr.size != 1 or not np.isfinite(arr.reshape(-1)[0]) or float(arr.reshape(-1)[0]) not in (4.0, 8.0):
            raise _err(
                "bwareaopen: connectivity must be 4 or 8",
                "OpenMATLAB:bwareaopen:Connectivity",
            )
        conn = int(arr.reshape(-1)[0])
    return (_logical(area_open(bw != 0, min_area, conn)),)


def register(builtins) -> None:
    builtins["graythresh"] = _graythresh
    builtins["imbinarize"] = _imbinarize
    builtins["bwareaopen"] = _bwareaopen
