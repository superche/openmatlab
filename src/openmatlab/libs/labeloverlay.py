"""``labeloverlay`` for one 2-D image (M16 I-E4, Epic #1023).

``B = labeloverlay(A, L)`` paints each positive label in ``L`` onto ``A``.
Label 0 is unchanged. A logical ``L`` treats true as label 1.

The color weight is ``w = 1 - Transparency``. ``Transparency`` is a scalar in
``[0, 1]``; the default is 0.5 (half the image, half the label color). On a
labeled pixel ``out = (1 - w) * image + w * color``.

``A`` is gray or RGB, uint8 or floating. uint8 is scaled by 255 and the result
is uint8 RGB, rounded to nearest with ties to even. A floating image is
treated as ``[0, 1]`` and the result is double RGB clipped to that range.

Label ``k`` (``k >= 1``) uses row ``(k - 1) mod 8`` of this fixed cycle.
These are not the MATLAB ``lines`` colors:

    228  26  28
     55 126 184
     77 175  74
    152  78 163
    255 127   0
    255 255  51
    166  86  40
    247 129 191

``Colormap`` and ``IncludedLabels`` are not accepted. This is not a copy of
an Image Processing Toolbox.
"""

from __future__ import annotations

import numpy as np

# RGB triples above, stored in [0, 1].
PALETTE = np.array(
    [
        [228, 26, 28],
        [55, 126, 184],
        [77, 175, 74],
        [152, 78, 163],
        [255, 127, 0],
        [255, 255, 51],
        [166, 86, 40],
        [247, 129, 191],
    ],
    dtype=np.float64,
) / 255.0


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


def _rgb(image: np.ndarray) -> tuple[np.ndarray, str]:
    if image.ndim == 2:
        planes, channels = image, 1
    elif image.ndim == 3 and image.shape[2] == 3:
        planes, channels = image, 3
    else:
        raise _err(
            "labeloverlay: image must be 2-D gray or RGB",
            "OpenMATLAB:labeloverlay:Dimension",
        )
    dt = planes.dtype
    if dt == np.uint8:
        rgb = planes.astype(np.float64) / 255.0
        kind = "uint8"
    elif dt == np.bool_ or np.issubdtype(dt, np.bool_):
        rgb = planes.astype(np.float64)
        kind = "double"
    elif np.issubdtype(dt, np.floating):
        if not np.all(np.isfinite(planes)):
            raise _err("labeloverlay: image must be finite", "OpenMATLAB:labeloverlay:BadImage")
        rgb = planes.astype(np.float64)
        kind = "double"
    else:
        raise _err(
            "labeloverlay: image class must be uint8 or floating",
            "OpenMATLAB:labeloverlay:Class",
        )
    if channels == 1:
        rgb = np.stack([rgb, rgb, rgb], axis=2)
    return rgb, kind


def _labels(mask: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    if mask.ndim != 2 or mask.shape != shape:
        raise _err(
            "labeloverlay: label matrix must be 2-D and the same size as the image",
            "OpenMATLAB:labeloverlay:Size",
        )
    if mask.dtype == np.bool_ or np.issubdtype(mask.dtype, np.bool_):
        return mask.astype(np.int64)
    if not np.issubdtype(mask.dtype, np.number):
        raise _err(
            "labeloverlay: labels must be nonnegative integers",
            "OpenMATLAB:labeloverlay:BadLabels",
        )
    if np.issubdtype(mask.dtype, np.floating) and not np.all(np.isfinite(mask)):
        raise _err("labeloverlay: labels must be finite", "OpenMATLAB:labeloverlay:BadLabels")
    if np.any(mask < 0) or np.any(mask != np.floor(mask)):
        raise _err(
            "labeloverlay: labels must be nonnegative integers",
            "OpenMATLAB:labeloverlay:BadLabels",
        )
    return np.asarray(mask, dtype=np.int64)


def _transparency(args) -> float:
    if len(args) % 2:
        raise _err(
            "labeloverlay: name-value arguments must come in pairs",
            "OpenMATLAB:labeloverlay:BadName",
        )
    value = 0.5
    for i in range(0, len(args), 2):
        name = _text(args[i])
        if name is None or name.lower() != "transparency":
            shown = name if name is not None else "parameter"
            raise _err(
                f"labeloverlay: unknown parameter '{shown}'",
                "OpenMATLAB:labeloverlay:BadName",
            )
        raw = _array(args[i + 1], "labeloverlay")
        if raw.size != 1 or not np.isfinite(raw).all():
            raise _err(
                "labeloverlay: Transparency must be a scalar between 0 and 1",
                "OpenMATLAB:labeloverlay:Transparency",
            )
        value = float(raw.reshape(-1)[0])
        if not 0.0 <= value <= 1.0:
            raise _err(
                "labeloverlay: Transparency must be a scalar between 0 and 1",
                "OpenMATLAB:labeloverlay:Transparency",
            )
    return value


def blend(image: np.ndarray, labels: np.ndarray, transparency: float = 0.5) -> np.ndarray:
    """Return RGB. uint8 in, uint8 out. Otherwise float64. Label 0 is copied."""
    raw = np.asarray(image)
    rgb, kind = _rgb(raw)
    lab = _labels(np.asarray(labels), (rgb.shape[0], rgb.shape[1]))
    if kind == "uint8":
        base = np.stack([raw, raw, raw], axis=2) if raw.ndim == 2 else np.asarray(raw, dtype=np.uint8)
    else:
        base = np.stack([raw, raw, raw], axis=2) if raw.ndim == 2 else raw.astype(np.float64)
        base = base.astype(np.float64)
    out = base.copy()
    fg = lab > 0
    weight = 1.0 - float(transparency)
    if np.any(fg) and weight != 0.0:
        color = PALETTE[(lab[fg] - 1) % PALETTE.shape[0]]
        mixed = (1.0 - weight) * rgb[fg] + weight * color
        if kind == "uint8":
            out[fg] = np.clip(np.rint(mixed * 255.0), 0, 255).astype(np.uint8)
        else:
            out[fg] = np.clip(mixed, 0.0, 1.0)
    return out


def _labeloverlay(args, *, nargout=1):
    from openmatlab.numerics.ndarray_value import NDArrayValue

    if len(args) < 2:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    image = _array(args[0], "labeloverlay")
    labels = _array(args[1], "labeloverlay")
    transparency = _transparency(args[2:])
    return (NDArrayValue(blend(image, labels, transparency)),)


def register(builtins) -> None:
    builtins["labeloverlay"] = _labeloverlay
