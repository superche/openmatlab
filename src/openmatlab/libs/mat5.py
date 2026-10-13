"""MAT-file Level 5 reader/writer, NumPy only (Epic #533).

Follows the public MathWorks "MAT-File Format" spec. Supported:
- double, single and int8..uint64 (real and complex);
- logical, char (including multi-row);
- cell, struct (scalar and arrays), sparse double/logical.

The reader also accepts miCOMPRESSED (zlib) elements, which MATLAB writes by
default. The writer emits uncompressed v5 (MATLAB reads both).
"""

from __future__ import annotations

import struct
import time
import zlib
from typing import Dict, List, Tuple

import numpy as np

miINT8, miUINT8, miINT16, miUINT16, miINT32, miUINT32 = 1, 2, 3, 4, 5, 6
miSINGLE, miDOUBLE, miINT64, miUINT64, miMATRIX, miCOMPRESSED = 7, 9, 12, 13, 14, 15
miUTF8, miUTF16 = 16, 17
_MI_DTYPE = {
    miINT8: np.int8, miUINT8: np.uint8, miINT16: np.int16, miUINT16: np.uint16,
    miINT32: np.int32, miUINT32: np.uint32, miSINGLE: np.float32, miDOUBLE: np.float64,
    miINT64: np.int64, miUINT64: np.uint64, miUTF8: np.uint8, miUTF16: np.uint16,
}
mxCELL, mxSTRUCT, mxOBJECT, mxCHAR, mxSPARSE, mxDOUBLE, mxSINGLE = 1, 2, 3, 4, 5, 6, 7
_MX_INT = {8: np.int8, 9: np.uint8, 10: np.int16, 11: np.uint16, 12: np.int32, 13: np.uint32, 14: np.int64, 15: np.uint64}
_DT_MX = {np.dtype(v): k for k, v in _MX_INT.items()}
_DT_MI = {np.dtype(np.int8): miINT8, np.dtype(np.uint8): miUINT8, np.dtype(np.int16): miINT16,
          np.dtype(np.uint16): miUINT16, np.dtype(np.int32): miINT32, np.dtype(np.uint32): miUINT32,
          np.dtype(np.int64): miINT64, np.dtype(np.uint64): miUINT64, np.dtype(np.float32): miSINGLE,
          np.dtype(np.float64): miDOUBLE}
F_COMPLEX, F_GLOBAL, F_LOGICAL = 0x0800, 0x0400, 0x0200


class MatError(ValueError):
    pass


# ----------------------------------------------------------------- writer
def _element(mi: int, data: bytes) -> bytes:
    pad = (-len(data)) % 8
    return struct.pack("<II", mi, len(data)) + data + b"\0" * pad


def _arr(mi: int, a: np.ndarray) -> bytes:
    return _element(mi, np.ascontiguousarray(a).astype(_MI_DTYPE[mi], copy=False).tobytes())


def _header(mx: int, flags: int, dims, name: str, nzmax: int = 0) -> bytes:
    out = _element(miUINT32, struct.pack("<II", (flags & 0xFF00) | mx, nzmax))
    out += _element(miINT32, np.asarray(dims, dtype=np.int32).tobytes())
    out += _element(miINT8, name.encode("ascii"))
    return out


def _matrix(v, name: str = "") -> bytes:
    return _element(miMATRIX, _matrix_body(v, name))


def _colmajor(buf: np.ndarray) -> np.ndarray:
    return np.asarray(buf).reshape(-1, order="F")


def _matrix_body(v, name: str) -> bytes:
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.char_value import CharValue

    if getattr(v, "is_struct", False):
        if getattr(v, "is_mexception", False):
            raise MatError("save: MException objects cannot be saved")
        dims = tuple(v.shape) if len(v.shape) >= 2 else (1, *v.shape)
        fields = list(v.fields)
        width = max([len(f) for f in fields] + [0]) + 1
        width = max(width, 1)
        body = _header(mxSTRUCT, 0, dims, name)
        body += _element(miINT32, struct.pack("<i", width))
        body += _element(miINT8, b"".join(f.encode("ascii").ljust(width, b"\0") for f in fields))
        for e in v.elems:
            for f in fields:
                body += _matrix(e[f])
        return body
    if isinstance(v, CellValue):
        dims = tuple(v.full_shape()) if v.nd else v.shape
        body = _header(mxCELL, 0, dims, name)
        r, c = v.shape
        for j in range(c):
            for i in range(r):
                body += _matrix(v.get(i, j))
        return body
    if getattr(v, "is_string", False):
        raise MatError("save: string arrays need MAT v7.3 objects; convert with char() first")
    if isinstance(v, CharValue):
        rows = list(v.rows)
        width = max([len(r) for r in rows] + [0])
        grid = np.array([[ord(ch) for ch in r.ljust(width)] for r in rows], dtype=np.uint16).reshape(len(rows), width)
        return _header(mxCHAR, 0, grid.shape if rows else (0, 0), name) + _arr(miUINT16, _colmajor(grid))
    if getattr(v, "issparse", False):
        st = v.store
        m, n = v.shape
        rows, cols, data = np.asarray(st.rows), np.asarray(st.cols), np.asarray(st.data)
        jc = np.searchsorted(cols, np.arange(n + 1)).astype(np.int32)
        logical = data.dtype == bool
        cplx = np.iscomplexobj(data)
        flags = (F_LOGICAL if logical else 0) | (F_COMPLEX if cplx else 0)
        body = _header(mxSPARSE, flags, (m, n), name, nzmax=max(1, len(data)))
        body += _arr(miINT32, rows.astype(np.int32)) + _arr(miINT32, jc)
        real = np.real(data).astype(np.float64)
        body += _arr(miDOUBLE, real)
        if cplx:
            body += _arr(miDOUBLE, np.imag(data).astype(np.float64))
        return body
    if hasattr(v, "backend_buffer"):
        a = np.asarray(v.backend_buffer())
        if a.ndim < 2:
            a = a.reshape(1, -1) if a.ndim == 1 else a.reshape(1, 1)
        flags = 0
        if a.dtype == bool:
            return _header(9, F_LOGICAL, a.shape, name) + _arr(miUINT8, _colmajor(a.astype(np.uint8)))
        cplx = np.iscomplexobj(a)
        if cplx:
            flags |= F_COMPLEX
        base = np.real(a) if cplx else a
        if base.dtype in _DT_MX:
            mx = _DT_MX[base.dtype]
        elif base.dtype == np.float32:
            mx = mxSINGLE
        else:
            base = base.astype(np.float64)
            mx = mxDOUBLE
        mi = _DT_MI[np.dtype(base.dtype)]
        body = _header(mx, flags, a.shape, name) + _arr(mi, _colmajor(base))
        if cplx:
            body += _arr(mi, _colmajor(np.imag(a).astype(base.dtype)))
        return body
    raise MatError(f"save: cannot save values of class {getattr(v, 'matlab_class', lambda: type(v).__name__)()}")


def write(path: str, variables: Dict[str, object]) -> None:
    text = f"MATLAB 5.0 MAT-file, Platform: openmatlab, Created on: {time.strftime('%a %b %d %H:%M:%S %Y')}"
    hdr = text.encode("ascii")[:116].ljust(116, b" ") + b"\0" * 8 + struct.pack("<H", 0x0100) + b"IM"
    body = b"".join(_matrix(v, n) for n, v in variables.items())
    with open(path, "wb") as fh:
        fh.write(hdr + body)


# ----------------------------------------------------------------- reader
def _read_tag(buf: bytes, pos: int, endian: str) -> Tuple[int, int, int, int]:
    """-> (type, nbytes, data_start, next_pos)"""
    if pos + 8 > len(buf):
        raise MatError("load: truncated MAT-file")
    t, n = struct.unpack(endian + "II", buf[pos:pos + 8])
    if t >> 16:  # small data element: type in low 16 bits, size in high 16
        return t & 0xFFFF, t >> 16, pos + 4, pos + 8
    return t, n, pos + 8, pos + 8 + n + ((-n) % 8)


def _read_elem(buf, pos, endian):
    t, n, s, nxt = _read_tag(buf, pos, endian)
    return t, buf[s:s + n], nxt


def _num(t, data, endian):
    if t not in _MI_DTYPE:
        raise MatError(f"load: unsupported data type {t}")
    return np.frombuffer(data, dtype=np.dtype(_MI_DTYPE[t]).newbyteorder(endian))


def _parse_matrix(data: bytes, endian: str):
    from openmatlab.numerics.ndarray_value import NDArrayValue
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.char_value import CharValue
    from openmatlab.runtime.struct_value import StructValue

    if not data:
        return "", NDArrayValue(np.zeros((0, 0)))
    pos = 0
    t, flags_b, pos = _read_elem(data, pos, endian)
    f0, nzmax = struct.unpack(endian + "II", flags_b[:8])
    mx, flags = f0 & 0xFF, f0 & 0xFF00
    t, dims_b, pos = _read_elem(data, pos, endian)
    dims = tuple(int(d) for d in _num(t, dims_b, endian))
    t, name_b, pos = _read_elem(data, pos, endian)
    name = bytes(name_b).decode("ascii", "replace")
    numel = int(np.prod(dims)) if dims else 0
    if mx == mxCELL:
        items = []
        for _ in range(numel):
            t, sub, pos = _read_elem(data, pos, endian)
            items.append(_parse_matrix(sub, endian)[1])
        r, c = (dims[0], int(np.prod(dims[1:]))) if len(dims) >= 2 else (1, numel)
        if numel == 0:
            return name, CellValue(rows=())
        rows = tuple(tuple(items[j * r + i] for j in range(c)) for i in range(r))
        return name, CellValue(rows=rows, nd=tuple(dims) if len(dims) > 2 else ())
    if mx in (mxSTRUCT, mxOBJECT):
        if mx == mxOBJECT:
            t, _cls, pos = _read_elem(data, pos, endian)
        t, w_b, pos = _read_elem(data, pos, endian)
        width = int(_num(t, w_b, endian)[0])
        t, names_b, pos = _read_elem(data, pos, endian)
        fields = [bytes(names_b[k:k + width]).split(b"\0", 1)[0].decode("ascii") for k in range(0, len(names_b), width)] if width else []
        elems = []
        for _ in range(numel):
            e = {}
            for f in fields:
                t, sub, pos = _read_elem(data, pos, endian)
                e[f] = _parse_matrix(sub, endian)[1]
            elems.append(e)
        return name, StructValue(tuple(dims), tuple(fields), tuple(elems))
    if mx == mxCHAR:
        t, ch_b, pos = _read_elem(data, pos, endian)
        if t == miUTF8:
            codes = list(bytes(ch_b).decode("utf-8"))
            codes = [ord(c) for c in codes]
        else:
            codes = _num(t, ch_b, endian).astype(np.int64).tolist()
        r, c = dims[0], int(np.prod(dims[1:])) if len(dims) > 1 else 1
        if r * c == 0:
            return name, CharValue("")
        grid = np.array(codes, dtype=np.int64).reshape((r, c), order="F")
        return name, CharValue(rows=tuple("".join(chr(x) for x in row) for row in grid))
    if mx == mxSPARSE:
        from openmatlab.numerics import sparse as sp

        t, ir_b, pos = _read_elem(data, pos, endian)
        t2, jc_b, pos = _read_elem(data, pos, endian)
        ir, jc = _num(t, ir_b, endian).astype(np.int64), _num(t2, jc_b, endian).astype(np.int64)
        t, pr_b, pos = _read_elem(data, pos, endian)
        pr = _num(t, pr_b, endian).astype(np.float64)
        if flags & F_COMPLEX:
            t, pi_b, pos = _read_elem(data, pos, endian)
            pr = pr + 1j * _num(t, pi_b, endian).astype(np.float64)
        nnz = int(jc[-1]) if len(jc) else 0
        cols = np.repeat(np.arange(len(jc) - 1), np.diff(jc))[:nnz]
        from openmatlab.numerics.sparse_store import Store

        vals = pr[:nnz] != 0 if flags & F_LOGICAL else pr[:nnz]
        return name, sp.from_store(Store(dims[0], dims[1], ir[:nnz], cols, vals))  # O(nnz), never dense
    # numeric / logical
    t, re_b, pos = _read_elem(data, pos, endian)
    re = _num(t, re_b, endian)
    if flags & F_COMPLEX:
        t, im_b, pos = _read_elem(data, pos, endian)
        re = re.astype(np.float64) + 1j * _num(t, im_b, endian).astype(np.float64)
    if flags & F_LOGICAL:
        out = re.astype(bool)
    elif mx == mxDOUBLE:
        out = re.astype(np.complex128 if np.iscomplexobj(re) else np.float64)
    elif mx == mxSINGLE:
        out = re.astype(np.complex64 if np.iscomplexobj(re) else np.float32)
    elif mx in _MX_INT:
        out = re.astype(_MX_INT[mx]) if not np.iscomplexobj(re) else re
    else:
        raise MatError(f"load: unsupported MATLAB class id {mx}")
    shape = dims if len(dims) >= 2 else (1, numel)
    return name, NDArrayValue(np.asarray(out).reshape(shape, order="F"))


def read(path: str) -> Dict[str, object]:
    with open(path, "rb") as fh:
        buf = fh.read()
    if len(buf) < 128 or not buf[:6].startswith(b"MATLAB"):
        raise MatError("load: not a MAT-file")
    endian = "<" if buf[126:128] == b"IM" else ">"
    if buf[126:128] not in (b"IM", b"MI"):
        raise MatError("load: bad MAT-file endian indicator")
    if b"MATLAB 7.3" in buf[:116]:
        raise MatError("load: MAT v7.3 (HDF5) files are not supported")
    out: Dict[str, object] = {}
    pos = 128
    while pos + 8 <= len(buf):
        t, n, s, nxt = _read_tag(buf, pos, endian)
        data = buf[s:s + n]
        if t == miCOMPRESSED:
            data = zlib.decompress(data)
            t2, n2, s2, _ = _read_tag(data, 0, endian)
            t, data = t2, data[s2:s2 + n2]
            nxt = s + n
        if t == miMATRIX:
            name, val = _parse_matrix(data, endian)
            out[name] = val
        pos = nxt
    return out
