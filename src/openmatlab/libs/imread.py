"""PNG ``imread`` for non-interlaced 8-bit and 16-bit images (M16 I-E1, Epic #1020).

BBBC038 ``stage1_test`` FOVs are 8-bit truecolor (color type 2) or truecolor
with alpha (color type 6). Grayscale (color types 0 and 4) is the same reader.
MATLAB returns the color samples in ``A``. Alpha, when the file has it, is the
third output, not a fourth page of ``A``.

Indexed color, Adam7 interlacing, and bit depths below 8 are rejected. Each
side is limited to 4096 pixels, which covers every stage1_test FOV (the largest
is 696 by 520). Decompression stops at the IHDR byte count.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

import numpy as np

_SIG = b"\x89PNG\r\n\x1a\n"
_SAMPLES = {0: 1, 2: 3, 4: 2, 6: 4}
_MAX_SIDE = 4096


def decode_png(data: bytes) -> tuple[np.ndarray, np.ndarray | None]:
    """Return ``(image, alpha)``. ``image`` is ``(H, W)`` or ``(H, W, 3)``.

    ``alpha`` is ``None`` when the file has no alpha channel, otherwise ``(H, W)``
    of the same integer class as ``image``.
    """
    ihdr, idat = _chunks(data)
    width, height, depth, color, comp, filt, inter = struct.unpack(">IIBBBBB", ihdr)
    if comp != 0 or filt != 0:
        raise RuntimeError("png compression or filter method is not 0")
    if inter != 0:
        raise RuntimeError("imread: interlaced PNG is not supported")
    if color not in _SAMPLES:
        raise RuntimeError(f"imread: PNG color type {color} is not supported")
    if depth not in (8, 16):
        raise RuntimeError(f"imread: PNG bit depth {depth} is not supported")
    if width <= 0 or height <= 0 or width > _MAX_SIDE or height > _MAX_SIDE:
        raise RuntimeError(f"imread: PNG size {width}x{height} is outside 1..{_MAX_SIDE}")
    channels = _SAMPLES[color]
    bpp = channels * (2 if depth == 16 else 1)
    stride = width * bpp
    raw = _inflate(idat, height * (stride + 1))
    recon = _unfilter(raw, height, stride, bpp)
    if depth == 16:
        pix = (recon[0::2].astype(np.uint16) << 8) | recon[1::2].astype(np.uint16)
        pix = pix.reshape(height, width, channels)
    else:
        pix = recon.reshape(height, width, channels)
    if color in (4, 6):
        color_px = pix[..., :-1]
        alpha = np.ascontiguousarray(pix[..., -1])
        image = color_px[..., 0] if color_px.shape[-1] == 1 else color_px
        return np.ascontiguousarray(image), alpha
    image = pix[..., 0] if channels == 1 else pix
    return np.ascontiguousarray(image), None


def _chunks(data: bytes) -> tuple[bytes, bytes]:
    if not data.startswith(_SIG):
        raise RuntimeError("imread: file is not a PNG")
    i = 8
    ihdr: bytes | None = None
    idat = bytearray()
    seen_idat = False
    while i + 12 <= len(data):
        length = struct.unpack(">I", data[i : i + 4])[0]
        typ = data[i + 4 : i + 8]
        start = i + 8
        end = start + length
        if end + 4 > len(data):
            raise RuntimeError("imread: PNG chunk is truncated")
        body = data[start:end]
        crc = struct.unpack(">I", data[end : end + 4])[0]
        if crc != (zlib.crc32(typ + body) & 0xFFFFFFFF):
            raise RuntimeError(f"imread: bad CRC for PNG chunk {typ.decode('ascii', 'replace')}")
        if ihdr is None:
            if typ != b"IHDR" or length != 13:
                raise RuntimeError("imread: PNG does not start with IHDR")
            ihdr = body
        elif typ == b"IDAT":
            idat.extend(body)
            seen_idat = True
        elif typ == b"IEND":
            if not seen_idat:
                raise RuntimeError("imread: PNG has no IDAT")
            return ihdr, bytes(idat)
        elif typ == b"PLTE":
            pass
        elif typ[0:1].isupper():
            raise RuntimeError(f"imread: unsupported PNG chunk {typ.decode('ascii', 'replace')}")
        i = end + 4
    raise RuntimeError("imread: PNG is missing IEND")


def _inflate(idat: bytes, need: int) -> bytes:
    dec = zlib.decompressobj()
    try:
        out = dec.decompress(idat, need)
    except zlib.error as exc:
        raise RuntimeError(f"imread: PNG IDAT could not be inflated: {exc}") from None
    if dec.unconsumed_tail:
        raise RuntimeError("imread: PNG IDAT is longer than the image")
    try:
        out += dec.flush()
    except zlib.error as exc:
        raise RuntimeError(f"imread: PNG IDAT could not be inflated: {exc}") from None
    if len(out) != need:
        raise RuntimeError(f"imread: PNG IDAT length {len(out)} != {need}")
    return out


def _unfilter(raw: bytes, height: int, stride: int, bpp: int) -> np.ndarray:
    src = np.frombuffer(raw, dtype=np.uint8)
    out = np.empty(height * stride, dtype=np.uint8)
    prev = bytearray(stride)
    for y in range(height):
        base = y * (stride + 1)
        kind = int(src[base])
        row = bytearray(src[base + 1 : base + 1 + stride])
        if kind == 0:
            pass
        elif kind == 1:
            for i in range(stride):
                left = row[i - bpp] if i >= bpp else 0
                row[i] = (row[i] + left) & 255
        elif kind == 2:
            for i in range(stride):
                row[i] = (row[i] + prev[i]) & 255
        elif kind == 3:
            for i in range(stride):
                left = row[i - bpp] if i >= bpp else 0
                row[i] = (row[i] + ((left + prev[i]) // 2)) & 255
        elif kind == 4:
            for i in range(stride):
                left = row[i - bpp] if i >= bpp else 0
                up = prev[i]
                ul = prev[i - bpp] if i >= bpp else 0
                row[i] = (row[i] + _paeth(left, up, ul)) & 255
        else:
            raise RuntimeError(f"imread: PNG filter {kind} is not supported")
        out[y * stride : (y + 1) * stride] = row
        prev = row
    return out


def _paeth(left: int, up: int, ul: int) -> int:
    estimate = left + up - ul
    dl, du, dul = abs(estimate - left), abs(estimate - up), abs(estimate - ul)
    if dl <= du and dl <= dul:
        return left
    if du <= dul:
        return up
    return ul


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _text(v, fn: str) -> str:
    from openmatlab.runtime.char_value import CharValue

    if isinstance(v, CharValue):
        return v.text
    if getattr(v, "is_string", False) and v.numel() == 1:
        return str(v.data.flat[0])
    raise _err(f"{fn}: filename must be a character vector or string scalar", "MATLAB:invalidType")


def _imread(args, *, nargout=1):
    """imread: PNG grayscale or RGB. Alpha is the third output when the file has one."""
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    if len(args) != 1:
        raise _err("Too many input arguments.", "MATLAB:TooManyInputs")
    if nargout > 3:
        raise _err("Too many output arguments.", "MATLAB:TooManyOutputs")
    path = Path(_text(args[0], "imread")).expanduser()
    if not path.is_file():
        raise _err(f"imread: file does not exist: {path}", "OpenMATLAB:imread:FileNotFound")
    try:
        image, alpha = decode_png(path.read_bytes())
    except RuntimeError as exc:
        raise _err(str(exc), "OpenMATLAB:imread:BadPng") from None
    from openmatlab.numerics.ndarray_value import NDArrayValue

    outs = [NDArrayValue(image)]
    if nargout >= 2:
        outs.append(NDArrayValue(np.zeros((0, 0), dtype=np.float64)))
    if nargout >= 3:
        if alpha is None:
            outs.append(NDArrayValue(np.zeros((0, 0), dtype=np.float64)))
        else:
            outs.append(NDArrayValue(alpha))
    return tuple(outs)


def register(builtins) -> None:
    builtins["imread"] = _imread
