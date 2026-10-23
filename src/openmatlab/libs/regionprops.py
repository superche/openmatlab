"""``bwlabel``, ``bwconncomp``, and a ``regionprops`` subset (M16 I-E3, Epic #1022).

Labels are 8-connected by default, 4-connected when asked. Object ids follow
the first foreground pixel in column-major order (down each column, columns
left to right). Background is 0.

``regionprops`` returns Area, Centroid, and Eccentricity. Centroid is
``[x y]`` with column ``x`` and row ``y``, 1-based. Eccentricity is
``sqrt(1 - λmin/λmax)`` of the second central moments of those coordinates.
A single pixel is 0. This is not a copy of the Octave image package.

``stage1_test`` has no mask files. The nucleus count is this labeling of the
opened mask from I-E2, with tolerance 0.
"""

from __future__ import annotations

import numpy as np

_PROPS = {"area": "Area", "centroid": "Centroid", "eccentricity": "Eccentricity"}


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


def _dscalar(value: float):
    from openmatlab.numerics.ndarray_value import NDArrayValue

    return NDArrayValue(np.array([[float(value)]], dtype=np.float64))


def _drow(values) -> object:
    from openmatlab.numerics.ndarray_value import NDArrayValue

    return NDArrayValue(np.asarray(list(values), dtype=np.float64).reshape(1, -1))


def _dcol(values) -> object:
    from openmatlab.numerics.ndarray_value import NDArrayValue

    data = np.asarray(list(values), dtype=np.float64).reshape(-1, 1)
    return NDArrayValue(data)


def label_image(mask: np.ndarray, conn: int = 8) -> tuple[np.ndarray, int]:
    """Return ``(labels, count)``. ``labels`` is float64, background 0."""
    fg = np.asarray(mask, dtype=bool)
    if fg.ndim != 2:
        raise _err("bwlabel: only 2-D images are supported", "OpenMATLAB:bwlabel:Dimension")
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

    if conn == 4:
        offsets = ((-1, 0), (0, -1))
    elif conn == 8:
        offsets = ((-1, 0), (-1, -1), (0, -1), (1, -1))
    else:
        raise _err("bwlabel: connectivity must be 4 or 8", "OpenMATLAB:bwlabel:Connectivity")

    nid = 0
    for col in range(width):
        for row in range(height):
            if not fg[row, col]:
                continue
            neighbors = []
            for dr, dc in offsets:
                rr, cc = row + dr, col + dc
                if rr < 0 or rr >= height or cc < 0 or cc >= width:
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
    roots = [find(i) for i in range(nid + 1)]
    mapping = np.zeros(nid + 1, dtype=np.int32)
    out = np.zeros((height, width), dtype=np.float64)
    count = 0
    for col in range(width):
        for row in range(height):
            lab = int(labels[row, col])
            if not lab:
                continue
            root = roots[lab]
            if mapping[root] == 0:
                count += 1
                mapping[root] = count
            out[row, col] = mapping[root]
    return out, count


def eccentricity(rows: np.ndarray, cols: np.ndarray) -> float:
    """Eccentricity from second central moments. ``rows`` and ``cols`` are 0-based."""
    if rows.size <= 1:
        return 0.0
    y = rows.astype(np.float64)
    x = cols.astype(np.float64)
    y = y - y.mean()
    x = x - x.mean()
    m20 = float(np.sum(x * x))
    m02 = float(np.sum(y * y))
    m11 = float(np.sum(x * y))
    delta = float(np.sqrt((m20 - m02) ** 2 + 4.0 * m11 * m11))
    major = (m20 + m02 + delta) / 2.0
    minor = (m20 + m02 - delta) / 2.0
    if major <= 0.0:
        return 0.0
    ratio = 0.0 if minor <= 0.0 else minor / major
    return float(np.sqrt(max(0.0, 1.0 - ratio)))


def _coords(labels: np.ndarray):
    count = int(labels.max()) if labels.size else 0
    objects = []
    for lab in range(1, count + 1):
        rows, cols = np.nonzero(labels == lab)
        objects.append((rows, cols))
    return objects


def _measure(rows: np.ndarray, cols: np.ndarray, props: tuple[str, ...]) -> dict:
    from openmatlab.numerics.ndarray_value import NDArrayValue

    area = int(rows.size)
    if area == 0:
        centroid = NDArrayValue(np.array([[np.nan, np.nan]], dtype=np.float64))
        ecc = np.nan
    else:
        centroid = _drow((float(cols.mean() + 1.0), float(rows.mean() + 1.0)))
        ecc = eccentricity(rows, cols)
    values = {
        "Area": _dscalar(area),
        "Centroid": centroid,
        "Eccentricity": _dscalar(ecc),
    }
    return {name: values[name] for name in props}


def _conn_arg(value, fn: str) -> int:
    word = _text(value)
    arr = None if word is not None else _array(value, fn)
    if word is not None or arr.size != 1 or not np.isfinite(arr.reshape(-1)[0]) or float(arr.reshape(-1)[0]) not in (4.0, 8.0):
        raise _err(f"{fn}: connectivity must be 4 or 8", "OpenMATLAB:bwlabel:Connectivity")
    return int(arr.reshape(-1)[0])


def _mask(args, fn: str) -> tuple[np.ndarray, int]:
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    if len(args) > 2:
        raise _err("Too many input arguments.", "MATLAB:TooManyInputs")
    data = _array(args[0], fn)
    if data.ndim != 2:
        raise _err(f"{fn}: only 2-D images are supported", "OpenMATLAB:bwlabel:Dimension")
    if np.issubdtype(data.dtype, np.floating) and np.any(~np.isfinite(data)):
        raise _err(f"{fn}: image must be finite", "OpenMATLAB:bwlabel:BadImage")
    conn = 8 if len(args) == 1 else _conn_arg(args[1], fn)
    return data != 0, conn


def _prop_names(args) -> tuple[str, ...]:
    from openmatlab.runtime.cell_value import CellValue

    if not args:
        return ("Area", "Centroid", "Eccentricity")
    found = []
    for arg in args:
        word = _text(arg)
        if word is not None:
            bits = [word]
        elif isinstance(arg, CellValue):
            bits = []
            for row in arg.rows:
                for item in row:
                    text = _text(item)
                    if text is None:
                        raise _err("regionprops: property name must be text", "OpenMATLAB:regionprops:BadProperty")
                    bits.append(text)
        else:
            raise _err("regionprops: property name must be text", "OpenMATLAB:regionprops:BadProperty")
        for bit in bits:
            key = bit.strip().lower()
            if key not in _PROPS:
                raise _err(
                    "regionprops: only Area, Centroid, and Eccentricity are supported",
                    "OpenMATLAB:regionprops:BadProperty",
                )
            found.append(_PROPS[key])
    return tuple(found)


def _objects_from_cc(cc):
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.struct_value import is_struct

    if not is_struct(cc) or not cc.has("PixelIdxList") or not cc.has("ImageSize"):
        raise _err("regionprops: expected a label image or a bwconncomp struct", "OpenMATLAB:regionprops:BadInput")
    hw = _array(cc.get("ImageSize"), "regionprops").reshape(-1)
    if hw.size < 2:
        raise _err("regionprops: ImageSize must be [rows cols]", "OpenMATLAB:regionprops:BadInput")
    height, width = int(hw[0]), int(hw[1])
    cell = cc.get("PixelIdxList")
    if not isinstance(cell, CellValue):
        raise _err("regionprops: PixelIdxList must be a cell array", "OpenMATLAB:regionprops:BadInput")
    objects = []
    ncols = cell.shape[1]
    for k in range(cell.numel()):
        i, j = divmod(k, ncols)
        idx = _array(cell.get(i, j), "regionprops").reshape(-1).astype(np.float64) - 1.0
        if idx.size and (np.any(idx < 0) or np.any(idx >= height * width)):
            raise _err("regionprops: pixel index is outside the image", "OpenMATLAB:regionprops:BadInput")
        rows = np.mod(idx, height).astype(np.int64)
        cols = np.floor(idx / height).astype(np.int64)
        objects.append((rows, cols))
    return objects


def _objects_from_image(image: np.ndarray):
    if image.ndim != 2:
        raise _err("regionprops: only 2-D images are supported", "OpenMATLAB:regionprops:Dimension")
    if image.dtype == np.bool_ or np.issubdtype(image.dtype, np.bool_):
        labels, _ = label_image(image, 8)
        return _coords(labels)
    if np.issubdtype(image.dtype, np.floating) and np.any(~np.isfinite(image)):
        raise _err("regionprops: image must be finite", "OpenMATLAB:regionprops:BadImage")
    if np.any(image < 0) or np.any(image != np.floor(image)):
        raise _err("regionprops: label image must be nonnegative integers", "OpenMATLAB:regionprops:BadImage")
    return _coords(np.asarray(image, dtype=np.float64))


def _bwlabel(args, *, nargout=1):
    from openmatlab.numerics.ndarray_value import NDArrayValue

    mask, conn = _mask(args, "bwlabel")
    labels, count = label_image(mask, conn)
    out = NDArrayValue(labels)
    if nargout >= 2:
        return (out, _dscalar(count))
    return (out,)


def _bwconncomp(args, *, nargout=1):
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.struct_value import StructValue

    mask, conn = _mask(args, "bwconncomp")
    labels, count = label_image(mask, conn)
    height = mask.shape[0]
    columns = []
    for lab in range(1, count + 1):
        rows, cols = np.nonzero(labels == lab)
        order = np.argsort(cols * height + rows, kind="mergesort")
        idx = rows[order] + cols[order] * height + 1
        columns.append(_dcol(idx.tolist()))
    if count == 0:
        cell = CellValue.empty(0, 1)
    else:
        cell = CellValue(rows=tuple((col,) for col in columns))
    return (StructValue.scalar([
        ("Connectivity", _dscalar(conn)),
        ("ImageSize", _drow((height, mask.shape[1]))),
        ("NumObjects", _dscalar(count)),
        ("PixelIdxList", cell),
    ]),)


def _regionprops(args, *, nargout=1):
    from openmatlab.runtime.struct_value import StructValue, is_struct

    if not args:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    props = _prop_names(args[1:])
    if is_struct(args[0]):
        objects = _objects_from_cc(args[0])
    else:
        objects = _objects_from_image(_array(args[0], "regionprops"))
    elems = [_measure(rows, cols, props) for rows, cols in objects]
    shape = (len(elems), 1) if elems else (0, 1)
    return (StructValue.build(shape, props, elems),)


def register(builtins) -> None:
    builtins["bwlabel"] = _bwlabel
    builtins["bwconncomp"] = _bwconncomp
    builtins["regionprops"] = _regionprops
