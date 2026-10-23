"""Formatted and file I/O, save/load (Epic #533).

Low-level I/O covers fopen/fclose, fprintf, fgetl/fgets, fscanf/sscanf,
fread/fwrite, feof/ftell/fseek/frewind, fileread, delete, tempname/tempdir,
fileparts/fullfile, isfile/isfolder and mkdir.

Text files (#549): textscan, dlmread/csvread, readmatrix, writematrix and
csvwrite/dlmwrite.

save/load use the MAT v5 codec in :mod:`openmatlab.libs.mat5`. They need the
caller's workspace, so they are frame intrinsics.

Files are always opened in binary mode. Text is Latin-1 so that bytes
round-trip, as with MATLAB's default for non-UTF-8 encodings.
"""

from __future__ import annotations

import fnmatch
import glob
import os
import re
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue

ENC = "latin-1"


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _char(t):
    from openmatlab.runtime.char_value import CharValue

    return CharValue(t)


def _num(x):
    return NDArrayValue(np.array([[float(x)]]))


def _text(v, fn, what="argument"):
    from openmatlab.runtime.char_value import CharValue

    if isinstance(v, CharValue):
        return v.text
    if getattr(v, "is_string", False) and v.numel() == 1:
        return str(v.data.flat[0])
    raise _err(f"{fn}: {what} must be a character vector or string scalar", "MATLAB:invalidType")


def _is_text(v):
    from openmatlab.runtime.char_value import CharValue

    return isinstance(v, CharValue) or (getattr(v, "is_string", False) and v.numel() == 1)


def _buf(v):
    return np.asarray(v.backend_buffer())


def _scalar(v, fn):
    b = _buf(v).reshape(-1)
    if b.size != 1:
        raise _err(f"{fn}: expected a scalar")
    return float(b[0])


# ----------------------------------------------------------------- file table
class _File:
    def __init__(self, fh, name, perm):
        self.fh, self.name, self.perm = fh, name, perm


_FILES: Dict[int, _File] = {}


def _get(fid_v, fn) -> _File:
    fid = int(_scalar(fid_v, fn))
    f = _FILES.get(fid)
    if f is None:
        raise _err("Invalid file identifier. Use fopen to generate a valid file identifier.", "MATLAB:FileIO:InvalidFid")
    return f


_PERMS = {"r": "rb", "w": "wb", "a": "ab", "r+": "r+b", "w+": "w+b", "a+": "a+b"}


def _fopen(args, *, nargout=1):
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    if not _is_text(args[0]):  # fopen(fid) -> [filename, permission]
        fid = int(_scalar(args[0], "fopen"))
        f = _FILES.get(fid)
        return (_char(f.name if f else ""), _char(f.perm if f else ""))
    name = _text(args[0], "fopen", "file name")
    if name == "all":
        return (NDArrayValue(np.array([sorted(_FILES)], dtype=float).reshape(1, -1)),)
    perm = _text(args[1], "fopen", "permission") if len(args) > 1 else "r"
    mode = _PERMS.get(perm.replace("t", "").replace("b", ""))
    if mode is None:
        raise _err(f"fopen: invalid permission '{perm}'", "MATLAB:fopen:InvalidPermission")
    try:
        fh = open(os.path.expanduser(name), mode)
    except OSError as exc:
        return (_num(-1), _char(exc.strerror or "Cannot open file."))
    fid = 3
    while fid in _FILES:
        fid += 1
    _FILES[fid] = _File(fh, name, perm)
    return (_num(fid), _char(""))


def _fclose(args, *, nargout=1):
    if len(args) != 1:
        raise _err("fclose: expected one argument")
    if _is_text(args[0]) and _text(args[0], "fclose") == "all":
        for f in _FILES.values():
            f.fh.close()
        _FILES.clear()
        return (_num(0),)
    fid = int(_scalar(args[0], "fclose"))
    if fid in (0, 1, 2):
        return (_num(0),)
    f = _FILES.pop(fid, None)
    if f is None:
        raise _err("Invalid file identifier. Use fopen to generate a valid file identifier.", "MATLAB:FileIO:InvalidFid")
    f.fh.close()
    return (_num(0),)


def _write_fid(fid: int, text: str) -> int:
    data = text.encode(ENC, "replace")
    if fid == 1:
        sys.stdout.write(text)
        sys.stdout.flush()
    elif fid == 2:
        sys.stderr.write(text)
        sys.stderr.flush()
    else:
        f = _FILES.get(fid)
        if f is None:
            raise _err("Invalid file identifier. Use fopen to generate a valid file identifier.", "MATLAB:FileIO:InvalidFid")
        f.fh.write(data)
    return len(data)


def _fprintf_text(args):
    from openmatlab.libs.text_builtins import _flat_args, _format

    if not args:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    fid = 1
    if not _is_text(args[0]) and hasattr(args[0], "backend_buffer"):
        if len(args) == 1:
            raise _err("fprintf: the format must be a character vector or string scalar", "MATLAB:fprintf:invalidFormat")
        fid = int(_scalar(args[0], "fprintf"))
        args = args[1:]
    fmt = _text(args[0], "fprintf", "format")
    return fid, _format(fmt, _flat_args(list(args[1:])))


def fprintf_builtin(args, *, nargout=1):
    fid, text = _fprintf_text(list(args))
    return (_num(_write_fid(fid, text)),)


def _fprintf_intrinsic(ev, args, nargout):
    fid, text = _fprintf_text(list(args))
    n = _write_fid(fid, text)
    return (_num(n),) if nargout >= 1 else ()


def _readline(f: _File, keep: bool):
    line = f.fh.readline()
    if not line:
        return _num(-1)
    t = line.decode(ENC)
    if not keep:
        t = t.rstrip("\n").rstrip("\r") if t.endswith("\n") else t
    return _char(t)


def _fgetl(args, *, nargout=1):
    return (_readline(_get(args[0], "fgetl"), False),)


def _fgets(args, *, nargout=1):
    return (_readline(_get(args[0], "fgets"), True),)


def _feof(args, *, nargout=1):
    f = _get(args[0], "feof")
    pos = f.fh.tell()
    at_end = f.fh.read(1) == b""
    f.fh.seek(pos)
    return (NDArrayValue(np.array([[at_end]])),)


def _ftell(args, *, nargout=1):
    return (_num(_get(args[0], "ftell").fh.tell()),)


def _frewind(args, *, nargout=1):
    _get(args[0], "frewind").fh.seek(0)
    return ()


def _fseek(args, *, nargout=1):
    f = _get(args[0], "fseek")
    off = int(_scalar(args[1], "fseek"))
    origin = 0
    if len(args) > 2:
        o = args[2]
        if _is_text(o):
            origin = {"bof": 0, "cof": 1, "eof": 2}.get(_text(o, "fseek"), None)
            if origin is None:
                raise _err("fseek: origin must be 'bof', 'cof' or 'eof'")
        else:
            origin = int(_scalar(o, "fseek")) + 1
    try:
        f.fh.seek(off, origin)
    except (OSError, ValueError):
        return (_num(-1),)
    return (_num(0),)


# ----------------------------------------------------------------- scanf
_SCAN_SPEC = re.compile(r"%(\*?)(\d*)(l|h)?([dioufeEgGxsc\[])|%%")
_FLOAT = re.compile(r"[+-]?(?:(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?|[Ii]nf|NaN|nan)")
_INT = re.compile(r"[+-]?\d+")


def _scan(text: str, fmt: str, limit: Optional[int] = None):
    """MATLAB sscanf core: apply ``fmt`` cyclically; return (values, all_char, count, pos)."""
    from openmatlab.libs.text_builtins import _escapes

    fmt = _escapes(fmt)
    vals: List[float] = []
    kinds = set()
    pos, n, count = 0, len(text), 0
    tokens = []
    k = 0
    for m in _SCAN_SPEC.finditer(fmt):
        if m.start() > k:
            tokens.append(("lit", fmt[k:m.start()]))
        tokens.append(("lit", "%") if m.group(0) == "%%" else ("spec", m))
        k = m.end()
    if k < len(fmt):
        tokens.append(("lit", fmt[k:]))
    if not any(t == "spec" for t, _ in tokens):
        return vals, False, 0, pos
    while pos <= n:
        progressed = False
        for kind, tok in tokens:
            if limit is not None and len(vals) >= limit:
                return vals, kinds == {"c"}, count, pos
            if kind == "lit":
                for ch in tok:
                    if ch.isspace():
                        while pos < n and text[pos].isspace():
                            pos += 1
                    elif pos < n and text[pos] == ch:
                        pos += 1
                    else:
                        return vals, bool(kinds) and kinds <= {"c"}, count, pos
                continue
            skip, width, _, conv = tok.group(1), tok.group(2), tok.group(3), tok.group(4)
            w = int(width) if width else None
            if conv != "c":
                while pos < n and text[pos].isspace():
                    pos += 1
            if pos >= n:
                return vals, bool(kinds) and kinds <= {"c"}, count, pos
            seg = text[pos:pos + w] if w else text[pos:]
            if conv in "dioux":
                if conv == "x":
                    mm = re.match(r"[0-9a-fA-F]+", seg)
                    val = float(int(mm.group(0), 16)) if mm else None
                else:
                    mm = _INT.match(seg)
                    if mm and conv in "di" and seg[mm.end():mm.end() + 1] in (".", "e", "E") and _FLOAT.match(seg):
                        # MATLAB %d stops before a fraction, leaving it unmatched
                        pass
                    val = float(int(mm.group(0))) if mm else None
                if mm is None:
                    return vals, bool(kinds) and kinds <= {"c"}, count, pos
                pos += mm.end()
                if not skip:
                    vals.append(val)
                    kinds.add("n")
                    count += 1
            elif conv in "feEgG":
                mm = _FLOAT.match(seg)
                if mm is None:
                    return vals, bool(kinds) and kinds <= {"c"}, count, pos
                pos += mm.end()
                if not skip:
                    vals.append(float(mm.group(0).replace("nan", "NaN").lower().replace("inf", "inf")))
                    kinds.add("n")
                    count += 1
            elif conv == "s":
                mm = re.match(r"\S+", seg)
                pos += mm.end()
                if not skip:
                    vals.extend(float(ord(c)) for c in mm.group(0))
                    kinds.add("c")
                    count += 1
            elif conv == "c":
                take = seg[: (w or 1)]
                pos += len(take)
                if not skip:
                    vals.extend(float(ord(c)) for c in take)
                    kinds.add("c")
                    count += 1
            else:
                raise _err(f"sscanf: unsupported conversion %{conv}")
            progressed = True
        if not progressed or pos >= n:
            break
    return vals, bool(kinds) and kinds <= {"c"}, count, pos


def _shape_out(vals, size_v, all_char):
    a = np.array(vals, dtype=float)
    if size_v is None:
        if all_char:
            return _char("".join(chr(int(x)) for x in a))
        return NDArrayValue(a.reshape(-1, 1))
    sz = _buf(size_v).reshape(-1)
    if sz.size == 1:
        lim = sz[0]
        a = a[: int(lim)] if np.isfinite(lim) else a
        out = a.reshape(-1, 1)
    else:
        m = int(sz[0])
        ncol = int(sz[1]) if np.isfinite(sz[1]) else int(np.ceil(a.size / m)) if m else 0
        a = a[: m * ncol]
        full = np.zeros(m * ncol)
        full[: a.size] = a
        out = full.reshape((m, ncol), order="F")
    if all_char:
        from openmatlab.runtime.char_value import CharValue

        return CharValue(rows=tuple("".join(chr(int(x)) for x in row) for row in np.atleast_2d(out)))
    return NDArrayValue(out)


def _limit(size_v):
    if size_v is None:
        return None
    sz = _buf(size_v).reshape(-1)
    tot = float(np.prod(sz))
    return int(tot) if np.isfinite(tot) else None


def _sscanf(args, *, nargout=1):
    if len(args) < 2:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    text, fmt = _text(args[0], "sscanf"), _text(args[1], "sscanf", "format")
    size_v = args[2] if len(args) > 2 else None
    vals, all_char, count, pos = _scan(text, fmt, _limit(size_v))
    out = _shape_out(vals, size_v, all_char)
    return (out, _num(count), _char("" if pos >= len(text.rstrip()) else "Matching failure in format."), _num(pos + 1))


def _fscanf(args, *, nargout=1):
    if len(args) < 2:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    f = _get(args[0], "fscanf")
    start = f.fh.tell()
    text = f.fh.read().decode(ENC)
    fmt = _text(args[1], "fscanf", "format")
    size_v = args[2] if len(args) > 2 else None
    vals, all_char, count, pos = _scan(text, fmt, _limit(size_v))
    f.fh.seek(start + len(text[:pos].encode(ENC)))
    return (_shape_out(vals, size_v, all_char), _num(count), _char(""))


# ----------------------------------------------------------------- binary
_PREC = {
    "uint8": np.uint8, "uchar": np.uint8, "unsigned char": np.uint8, "int8": np.int8, "schar": np.int8,
    "signed char": np.int8, "char": np.uint8, "char*1": np.uint8, "int16": np.int16, "uint16": np.uint16,
    "int32": np.int32, "uint32": np.uint32, "int64": np.int64, "uint64": np.uint64, "int": np.int32,
    "single": np.float32, "float32": np.float32, "float": np.float32, "double": np.float64,
    "float64": np.float64, "short": np.int16, "long": np.int64, "ushort": np.uint16, "uint": np.uint32,
}


def _precision(p: str):
    """'uint8' -> (in, out='double'); '*uint8' -> same class; 'uint8=>char'."""
    p = p.strip()
    out = "double"
    if p.startswith("*"):
        p = p[1:]
        out = p
    elif "=>" in p:
        p, out = (x.strip() for x in p.split("=>", 1))
    if p not in _PREC:
        raise _err(f"fread: invalid precision '{p}'", "MATLAB:fread:InvalidPrecision")
    return p, out


def _fread(args, *, nargout=1):
    f = _get(args[0], "fread")
    size_v = args[1] if len(args) > 1 and not _is_text(args[1]) else None
    rest = [a for a in args[1:] if _is_text(a)]
    pin, pout = _precision(_text(rest[0], "fread")) if rest else ("uint8", "double")
    dt = np.dtype(_PREC[pin])
    lim = _limit(size_v)
    raw = f.fh.read() if lim is None else f.fh.read(lim * dt.itemsize)
    k = len(raw) // dt.itemsize
    vals = np.frombuffer(raw[: k * dt.itemsize], dtype=dt.newbyteorder("<"))
    count = vals.size
    if size_v is not None and _buf(size_v).size == 2:
        sz = _buf(size_v).reshape(-1)
        m = int(sz[0])
        ncol = int(sz[1]) if np.isfinite(sz[1]) else int(np.ceil(vals.size / m)) if m else 0
        full = np.zeros(m * ncol, dtype=vals.dtype)
        full[: min(vals.size, m * ncol)] = vals[: m * ncol]
        shaped = full.reshape((m, ncol), order="F")
    else:
        shaped = vals.reshape(-1, 1)
    if pout == "char" or (pin.startswith("char") and pout == "char"):
        from openmatlab.runtime.char_value import CharValue

        return (CharValue(rows=tuple("".join(chr(int(x)) for x in row) for row in shaped.T.T) if shaped.size else ()), _num(count))
    if pout == "double":
        out = shaped.astype(np.float64)
    else:
        out = shaped.astype(_PREC.get(pout, np.float64))
    return (NDArrayValue(out), _num(count))


def _fwrite(args, *, nargout=1):
    f = _get(args[0], "fwrite")
    if len(args) < 2:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    v = args[1]
    if _is_text(v):
        a = np.array([ord(c) for c in _text(v, "fwrite")], dtype=float)
    else:
        a = _buf(v).reshape(-1, order="F").astype(float) if _buf(v).dtype != bool else _buf(v).reshape(-1, order="F").astype(float)
    prec = _precision(_text(args[2], "fwrite"))[0] if len(args) > 2 else "uint8"
    dt = np.dtype(_PREC[prec])
    if np.issubdtype(dt, np.integer):
        info = np.iinfo(dt)
        a = np.clip(np.round(np.nan_to_num(a)), info.min, info.max)
    f.fh.write(a.astype(dt.newbyteorder("<")).tobytes())
    return (_num(a.size),)


# ----------------------------------------------------------------- files
def _fileread(args, *, nargout=1):
    name = _text(args[0], "fileread", "file name")
    try:
        return (_char(Path(name).expanduser().read_bytes().decode(ENC)),)
    except OSError:
        raise _err(f"Could not open file {name}. No such file or directory.", "MATLAB:fileread:cannotOpenFile") from None


def _delete(args, *, nargout=1):
    for a in args:
        pat = os.path.expanduser(_text(a, "delete", "file name"))
        hits = glob.glob(pat) if any(c in pat for c in "*?[") else ([pat] if os.path.exists(pat) else [])
        if not hits:
            from openmatlab.runtime import warnings as _w

            _w.emit(f"File '{pat}' not found.", "MATLAB:DELETE:FileNotFound")
            continue
        for h in hits:
            if os.path.isdir(h):
                raise _err(f"delete: '{h}' is a folder; use rmdir", "MATLAB:DELETE:Permission")
            os.remove(h)
    return ()


def _tempdir(args, *, nargout=1):
    return (_char(tempfile.gettempdir().rstrip(os.sep) + os.sep),)


def _tempname(args, *, nargout=1):
    base = _text(args[0], "tempname") if args else tempfile.gettempdir()
    return (_char(os.path.join(base, "tp" + uuid.uuid4().hex[:12])),)


def _fileparts(args, *, nargout=1):
    p = _text(args[0], "fileparts")
    head, tail = os.path.split(p)
    if p.endswith("/"):
        head, tail = p.rstrip("/") or "/", ""
    name, ext = os.path.splitext(tail)
    if tail.startswith(".") and name == tail:
        name, ext = "", tail
    return (_char(head), _char(name), _char(ext))


def _fullfile(args, *, nargout=1):
    parts = [_text(a, "fullfile") for a in args]
    parts = [p for p in parts if p != ""]
    if not parts:
        return (_char(""),)
    out = parts[0]
    for p in parts[1:]:
        out = out.rstrip("/") + "/" + p.lstrip("/")
    return (_char(re.sub(r"/+", "/", out)),)


def _isfile(args, *, nargout=1):
    return (NDArrayValue(np.array([[os.path.isfile(os.path.expanduser(_text(args[0], "isfile")))]])),)


def _isfolder(args, *, nargout=1):
    return (NDArrayValue(np.array([[os.path.isdir(os.path.expanduser(_text(args[0], "isfolder")))]])),)


def _mkdir(args, *, nargout=1):
    parts = [_text(a, "mkdir") for a in args]
    path = os.path.join(*parts) if parts else ""
    if os.path.isdir(path):
        return (NDArrayValue(np.array([[True]])), _char("Directory already exists."), _char("MATLAB:MKDIR:DirectoryExists"))
    try:
        os.makedirs(path)
    except OSError as exc:
        return (NDArrayValue(np.array([[False]])), _char(str(exc)), _char("MATLAB:MKDIR:OSError"))
    return (NDArrayValue(np.array([[True]])), _char(""), _char(""))


def _rmdir(args, *, nargout=1):
    import shutil

    path = _text(args[0], "rmdir")
    rec = len(args) > 1 and _text(args[1], "rmdir") == "s"
    try:
        shutil.rmtree(path) if rec else os.rmdir(path)
    except OSError as exc:
        if nargout >= 1:
            return (NDArrayValue(np.array([[False]])), _char(str(exc)))
        raise _err(f"rmdir: {exc.strerror}", "MATLAB:RMDIR:OSError") from None
    return (NDArrayValue(np.array([[True]])), _char(""))


# ----------------------------------------------------------------- text tables
def _sniff(lines):
    for d in (",", "\t", ";"):
        if any(d in ln for ln in lines[:5]):
            return d
    return None


def _to_float(tok: str, empty=np.nan):
    t = tok.strip()
    if t == "":
        return empty
    try:
        return float(t.replace("i", "j")) if "i" not in t else complex(t.replace("i", "j")).real
    except ValueError:
        return None


def _read_table(name, delim=None, empty=np.nan, skip_header=True, r0=0, c0=0):
    try:
        lines = Path(name).expanduser().read_text(encoding=ENC).splitlines()
    except OSError:
        raise _err(f"Unable to find or open '{name}'. Check the path and filename or file permissions.", "MATLAB:textio:textio:FileNotFound") from None
    lines = [ln for ln in lines if ln.strip() != ""]
    d = delim if delim is not None else _sniff(lines)
    rows = []
    for ln in lines:
        # A space delimiter collapses padding runs, the same way readtable does.
        # C-MAPSS rows are space-padded; consecutive spaces are not empty fields.
        toks = ln.split() if d in (None, "", " ") else ln.split(d)
        vals = [_to_float(t, empty) for t in toks]
        if any(v is None for v in vals):
            if skip_header and not rows:
                continue  # header line
            vals = [np.nan if v is None else v for v in vals]
        rows.append(vals)
    rows = rows[r0:]
    w = max((len(r) for r in rows), default=0)
    a = np.full((len(rows), w), empty, dtype=float)
    for i, r in enumerate(rows):
        a[i, : len(r)] = r
    return a[:, c0:]


def _readmatrix(args, *, nargout=1):
    name = _text(args[0], "readmatrix")
    delim = None
    i = 1
    while i + 1 < len(args):
        if _text(args[i], "readmatrix").lower() == "delimiter":
            raw = _text(args[i + 1], "readmatrix")
            delim = " " if raw.lower() == "space" else raw
        i += 2
    return (NDArrayValue(_read_table(name, delim, np.nan)),)


def _dlmread(args, *, nargout=1):
    name = _text(args[0], "dlmread")
    delim = None
    nums = []
    for a in args[1:]:
        if _is_text(a):
            delim = _text(a, "dlmread").replace("\\t", "\t")
        else:
            nums.append(int(_scalar(a, "dlmread")))
    r0, c0 = (nums + [0, 0])[:2]
    return (NDArrayValue(_read_table(name, delim, 0.0, skip_header=False, r0=r0, c0=c0)),)


def _csvread(args, *, nargout=1):
    nums = [a for a in args[1:]]
    return _dlmread([args[0], _char(","), *nums])


def _fmt_num(x, prec):
    if np.isnan(x):
        return "NaN"
    if np.isinf(x):
        return "Inf" if x > 0 else "-Inf"
    return prec % x


def _write_table(name, a, delim, prec):
    a = np.atleast_2d(np.asarray(a, dtype=float))
    text = "".join(delim.join(_fmt_num(x, prec) for x in row) + "\n" for row in a)
    Path(name).expanduser().write_text(text, encoding=ENC)


def _writematrix(args, *, nargout=1):
    a = _buf(args[0])
    name = _text(args[1], "writematrix") if len(args) > 1 else "matrix.txt"
    delim = ","
    i = 2
    while i + 1 < len(args):
        if _text(args[i], "writematrix").lower() == "delimiter":
            d = _text(args[i + 1], "writematrix")
            delim = {"tab": "\t", "\\t": "\t", "space": " ", "comma": ",", "semi": ";", "bar": "|"}.get(d, d)
        i += 2
    _write_table(name, a, delim, "%.15g")
    return ()


def _dlmwrite(args, *, nargout=1):
    name = _text(args[0], "dlmwrite")
    a = _buf(args[1])
    delim, prec, append, nl, r0, c0 = ",", "%.5g", False, "\n", 0, 0
    rest = [x for x in args[2:]]
    if "-append" in [_text(x, "dlmwrite").lower() if _is_text(x) else None for x in rest]:  # M3-E5 #629
        append = True
        rest = [x for x in rest if not (_is_text(x) and _text(x, "dlmwrite").lower() == "-append")]
    keys = ("delimiter", "precision", "newline", "roffset", "coffset")
    if rest and _is_text(rest[0]) and _text(rest[0], "dlmwrite").lower() not in keys:
        delim = _text(rest.pop(0), "dlmwrite").replace("\\t", "\t")
        nums = []
        while rest and not _is_text(rest[0]) and len(nums) < 2:
            nums.append(int(_scalar(rest.pop(0), "dlmwrite")))
        r0, c0 = (nums + [0, 0])[:2]
    while len(rest) >= 2:
        k, v = _text(rest[0], "dlmwrite").lower(), rest[1]
        if k == "delimiter":
            delim = _text(v, "dlmwrite").replace("\\t", "\t")
        elif k == "precision":
            prec = _text(v, "dlmwrite") if _is_text(v) else f"%.{int(_scalar(v, 'dlmwrite'))}g"
        elif k == "newline":
            nl = "\r\n" if _text(v, "dlmwrite").lower() == "pc" else "\n"
        elif k == "roffset":
            r0 = int(_scalar(v, "dlmwrite"))
        elif k == "coffset":
            c0 = int(_scalar(v, "dlmwrite"))
        else:
            raise _err(f"dlmwrite: unknown option '{k}'")
        rest = rest[2:]
    a = np.atleast_2d(np.asarray(a, dtype=float))
    lines = [delim * (a.shape[1] + c0 - 1 if a.size else 0)] * r0
    lines += [delim * c0 + delim.join(_fmt_num(x, prec) for x in row) for row in a]
    text = "".join(line + nl for line in lines)
    p = Path(name).expanduser()
    with open(p, "a" if append else "w", encoding=ENC, newline="") as fh:
        fh.write(text)
    return ()


def _csvwrite(args, *, nargout=1):
    return _dlmwrite([args[0], args[1], _char(",")])


def _textscan(args, *, nargout=1):
    from openmatlab.runtime.cell_value import CellValue

    if len(args) < 2:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    if _is_text(args[0]):
        text = _text(args[0], "textscan")
        f = None
    else:
        f = _get(args[0], "textscan")
        text = f.fh.read().decode(ENC)
    fmt = _text(args[1], "textscan", "format")
    delim, header = None, 0
    i = 2
    if i < len(args) and not _is_text(args[i]):
        i += 1  # repeat count: not modelled
    while i + 1 < len(args):
        k = _text(args[i], "textscan").lower()
        if k == "delimiter":
            delim = _text(args[i + 1], "textscan").replace("\\t", "\t")
        elif k == "headerlines":
            header = int(_scalar(args[i + 1], "textscan"))
        i += 2
    specs = re.findall(r"%(\*?)\d*(?:\.\d+)?([dfsuqn]|f32|f64|d8|d16|d32|d64|u8|u16|u32|u64)", fmt)
    if not specs:
        raise _err("textscan: the format has no conversions")
    cols = [[] for _ in specs]
    for ln in text.splitlines()[header:]:
        if ln.strip() == "":
            continue
        toks = [t.strip() for t in ln.split(delim)] if delim else ln.split()
        for k, (skip, conv) in enumerate(specs):
            tok = toks[k] if k < len(toks) else ""
            if conv[0] in "dfun":
                v = _to_float(tok)
                cols[k].append(np.nan if v is None else v)
            else:
                cols[k].append(tok.strip('"') if conv == "q" else tok)
    out = []
    for (skip, conv), c in zip(specs, cols):
        if skip:
            continue
        if conv[0] in "dfun":
            a = np.array(c, dtype=float).reshape(-1, 1)
            if conv[0] in "du":
                dt = {"d": np.int32, "u": np.uint32}[conv[0]]
                a = np.round(np.nan_to_num(a)).astype(dt) if conv in ("d", "u") else a
            out.append(NDArrayValue(a))
        else:
            out.append(CellValue(rows=tuple((_char(s),) for s in c)) if c else CellValue(rows=()))
    return (CellValue(rows=(tuple(out),)),)


# ----------------------------------------------------------------- save/load
def _mat_name(name: str) -> str:
    return name if os.path.splitext(name)[1] else name + ".mat"


def _save(ev, args, nargout):
    from openmatlab.libs import mat5

    texts = [_text(a, "save") for a in args]
    opts = [t for t in texts if t.startswith("-")]
    words = [t for t in texts if not t.startswith("-")]
    fname = _mat_name(words[0]) if words else "matlab.mat"
    names = words[1:]
    struct_mode = "-struct" in opts
    ascii_mode = "-ascii" in opts
    variables: Dict[str, object] = {}
    if struct_mode:
        if not names:
            raise _err("save: -struct needs a structure variable name", "MATLAB:save:noStructName")
        sv = ev.workspace.get(names[0]) if names[0] in ev.workspace else None
        if sv is None or not getattr(sv, "is_struct", False) or sv.numel() != 1:
            raise _err(f"The argument to -STRUCT must be the name of a scalar structure variable.", "MATLAB:save:structArgMustBeScalarStruct")
        flds = names[1:] or list(sv.fields)
        for fld in flds:
            variables[fld] = sv.elems[0][fld]
    else:
        visible = sorted(ev.workspace.names())
        if not names:
            names = visible
        for pat in names:
            hit = [n for n in visible if fnmatch.fnmatchcase(n, pat)]
            if not hit:
                raise _err(f"Variable '{pat}' not found.", "MATLAB:save:couldNotWriteFile")
            for n in hit:
                if n != "ans" or pat == "ans":
                    variables[n] = ev.workspace.get(n)
    if ascii_mode:
        fname = words[0] if words else "matlab.txt"
        lines = []
        for v in variables.values():
            a = np.atleast_2d(np.asarray(v.backend_buffer(), dtype=float))
            lines.extend(" ".join(f"{x: .7e}" for x in row) for row in a)
        Path(fname).write_text("\n".join(lines) + "\n")
        return ()
    if "-append" in opts and os.path.exists(fname):
        try:
            old = mat5.read(fname)
        except mat5.MatError as exc:
            raise _err(str(exc), "MATLAB:save:couldNotWriteFile") from None
        old.update(variables)
        variables = old
    try:
        mat5.write(fname, variables)
    except mat5.MatError as exc:
        raise _err(str(exc), "MATLAB:save:unsupportedType") from None
    except OSError as exc:
        raise _err(f"Unable to write file {fname}: {exc.strerror}.", "MATLAB:save:permissionDenied") from None
    return ()


def _revive(ev, var, v):
    """A struct read from an mxOBJECT element becomes an instance of its class again (M8 O-E7).

    Like MATLAB, the constructor is not called: the object starts from its class
    defaults and gets the saved property values.
    """
    from openmatlab.runtime import classdef as cd

    cls = getattr(v, "mat_class", None)
    if not cls or not getattr(v, "is_struct", False) or v.numel() != 1:
        return v
    info = cd.lookup(ev.functions, cls)
    if info is None:
        from openmatlab.runtime import warnings as _w

        _w.emit(f"Variable '{var}' originally saved as a {cls} cannot be instantiated as an object and will be "
                "read in as a struct.", "MATLAB:load:classNotFound")
        return v
    obj = info.new_instance()
    for f in v.fields:
        p = info.find_prop(f)
        if p is not None and not (p.constant or p.dependent):
            obj.props[f] = _revive(ev, f, v.get(f))
    return obj


def _load(ev, args, nargout):
    from openmatlab.libs import mat5
    from openmatlab.runtime.struct_value import StructValue

    texts = [_text(a, "load") for a in args]
    opts = [t for t in texts if t.startswith("-")]
    words = [t for t in texts if not t.startswith("-")]
    fname = words[0] if words else "matlab.mat"
    names = words[1:]
    path = fname if os.path.exists(fname) else _mat_name(fname)
    if not os.path.exists(path):
        raise _err(f"Unable to find file or directory '{fname}'.", "MATLAB:load:couldNotReadFile")
    with open(path, "rb") as fh:
        is_mat = fh.read(6) == b"MATLAB"
    if "-ascii" in opts or not is_mat:
        try:
            a = _read_table(path, None, np.nan, skip_header=False)
        except Exception:
            raise _err(f"Unable to read file '{fname}'. Input must be a MAT-file or an ASCII file containing numeric data with same number of columns in each row.", "MATLAB:load:unableToReadAsciiFile") from None
        if np.isnan(a).any() and not np.isnan(a).all():
            raise _err(f"Unable to read file '{fname}'. Input must be a MAT-file or an ASCII file containing numeric data with same number of columns in each row.", "MATLAB:load:unableToReadAsciiFile")
        var = re.sub(r"\W", "_", Path(path).stem)
        var = var if var and var[0].isalpha() else "X" + var
        data = {var: NDArrayValue(a)}
    else:
        try:
            data = mat5.read(path)
        except mat5.MatError as exc:
            raise _err(str(exc), "MATLAB:load:unableToRead") from None
    data = {k: _revive(ev, k, v) for k, v in data.items()}
    if names:
        sel = {}
        for pat in names:
            hit = [k for k in data if fnmatch.fnmatchcase(k, pat)]
            if not hit:
                from openmatlab.runtime import warnings as _w

                _w.emit(f"Variable '{pat}' not found.", "MATLAB:load:variableNotFound")
            for k in hit:
                sel[k] = data[k]
        data = sel
    if nargout >= 1:
        return (StructValue.scalar(list(data.items())),)
    for k, v in data.items():
        ev.workspace.set(k, v)
    return ()


BUILTINS = {
    "fopen": _fopen, "fclose": _fclose, "fprintf": fprintf_builtin, "fgetl": _fgetl, "fgets": _fgets,
    "feof": _feof, "ftell": _ftell, "frewind": _frewind, "fseek": _fseek, "sscanf": _sscanf,
    "fscanf": _fscanf, "fread": _fread, "fwrite": _fwrite, "fileread": _fileread, "delete": _delete,
    "tempdir": _tempdir, "tempname": _tempname, "fileparts": _fileparts, "fullfile": _fullfile,
    "isfile": _isfile, "isfolder": _isfolder, "mkdir": _mkdir, "rmdir": _rmdir,
    "readmatrix": _readmatrix, "dlmread": _dlmread, "csvread": _csvread, "writematrix": _writematrix,
    "dlmwrite": _dlmwrite, "csvwrite": _csvwrite, "textscan": _textscan,
}
INTRINSICS = {"save": _save, "load": _load, "fprintf": _fprintf_intrinsic}
STATEMENT_ZERO = {"save", "load", "fprintf"}


def register(builtins) -> None:
    for k, v in BUILTINS.items():
        builtins.setdefault(k, v)
