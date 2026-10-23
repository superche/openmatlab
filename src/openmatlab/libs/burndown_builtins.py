"""Missing base-MATLAB functions found by the corpus (#766 burn-down, missing-builtin group).

Text: strtok isspace findstr strmatch base2dec strjust validatestring getenv vectorize.
Arrays/matrices: repelem rref pascal hankel hadamard spiral vander hilb invhilb rosser wilkinson
compan polyvalm gradient del2 conv2 filter2 rat legendre.
Elementary: reallog realsqrt realpow erfcx and the degree/hyperbolic reciprocal trig family
(secd cscd cotd asecd acscd acotd sech csch coth asech acsch acoth).

Clean-room implementations from the documented behaviour and standard mathematical
definitions (NumPy only); no MATLAB or Octave source was consulted.
"""

from __future__ import annotations

import math
import os
from fractions import Fraction
from typing import Callable, Dict

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _cv(s):
    from openmatlab.runtime.char_value import CharValue

    return CharValue(s)


def _is_text(v):
    from openmatlab.runtime.char_value import CharValue

    return isinstance(v, CharValue)


def _is_cell(v):
    from openmatlab.runtime.cell_value import CellValue

    return isinstance(v, CellValue)


def _cell(items, shape):
    from openmatlab.runtime.cell_value import CellValue

    r, c = shape
    return CellValue(rows=tuple(tuple(items[j * r + i] for j in range(c)) for i in range(r)))


def _num(v, fn):
    buf = getattr(v, "backend_buffer", None)
    if buf is None or _is_text(v) and False:
        raise _err(f"Undefined function '{fn}' for input arguments of type '{v.matlab_class()}'.", "MATLAB:UndefinedFunction")
    if _is_text(v):
        return np.array([[ord(ch) for ch in v.text]], dtype=float)
    a = np.asarray(buf())
    if a.dtype == np.bool_ or a.dtype.kind in "iu":
        a = a.astype(np.float64)
    return a.reshape(1, 1) if a.ndim == 0 else a


def _out(a):
    a = np.asarray(a)
    if np.iscomplexobj(a) and not np.any(a.imag):
        a = a.real
    if a.ndim == 0:
        a = a.reshape(1, 1)
    elif a.ndim == 1:
        a = a.reshape(1, -1)
    return NDArrayValue(a)


def _scalar(v, fn):
    a = _num(v, fn).reshape(-1)
    if a.size != 1:
        raise _err(f"{fn}: argument must be a scalar.", f"MATLAB:{fn}:InvalidInput")
    return float(a[0])


def _need(args, n, fn):
    if len(args) < n:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")


def _cellstrs(v):
    r, c = v.shape
    return [v.get(i, j) for j in range(c) for i in range(r)]


# ---- text --------------------------------------------------------------------------------
def _strtok(args, *, nargout=1):
    _need(args, 1, "strtok")
    s = args[0]
    delims = " \t\n\v\f\r\x00" if len(args) < 2 else args[1].text
    if _is_cell(s):
        toks, rems = [], []
        for x in _cellstrs(s):
            t, r = _tok(x.text, delims)
            toks.append(_cv(t))
            rems.append(_cv(r))
        out = (_cell(toks, s.shape), _cell(rems, s.shape))
        return out[:max(nargout, 1)]
    if not _is_text(s):
        raise _err("strtok: first argument must be a character vector, string or cell array of character vectors.",
                   "MATLAB:strtok:InvalidInput")
    t, r = _tok(s.text, delims)
    mk = type(s) if getattr(s, "is_string", False) else _cv
    return (mk(t), mk(r))[:max(nargout, 1)]


def _tok(s, delims):
    i = 0
    while i < len(s) and s[i] in delims:
        i += 1
    j = i
    while j < len(s) and s[j] not in delims:
        j += 1
    return s[i:j], s[j:]


def _isspace(args, *, nargout=1):
    _need(args, 1, "isspace")
    v = args[0]
    if not _is_text(v):
        a = _num(v, "isspace")
        return (NDArrayValue(np.zeros(a.shape, dtype=bool)),)
    rows = v.rows
    out = np.array([[ch in " \t\n\v\f\r" for ch in r] for r in rows], dtype=bool) if rows else np.zeros((0, 0), bool)
    return (NDArrayValue(out),)


def _findstr(args, *, nargout=1):
    _need(args, 2, "findstr")
    a, b = args[0].text, args[1].text
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return (NDArrayValue(np.zeros((1, 0))),)
    idx = [i + 1 for i in range(len(a) - len(b) + 1) if a[i:i + len(b)] == b]
    return (NDArrayValue(np.array([idx], dtype=float).reshape(1, -1)) if idx else NDArrayValue(np.zeros((1, 0))),)


def _strmatch(args, *, nargout=1):
    _need(args, 2, "strmatch")
    pat = args[0].text
    exact = len(args) > 2 and _is_text(args[2]) and args[2].text == "exact"
    lst = [x.text for x in _cellstrs(args[1])] if _is_cell(args[1]) else list(args[1].rows)
    hits = []
    for i, s in enumerate(lst):
        t = s.rstrip(" \x00") if exact else s
        if (t == pat) if exact else s.startswith(pat):
            hits.append(i + 1)
    return (NDArrayValue(np.array(hits, dtype=float).reshape(-1, 1)) if hits else NDArrayValue(np.zeros((0, 1))),)


def _base2dec(args, *, nargout=1):
    _need(args, 2, "base2dec")
    b = args[1]
    if _is_text(b):
        digits = b.text
        base = len(digits)
        lut = {ch: i for i, ch in enumerate(digits)}
    else:
        base = int(_scalar(b, "base2dec"))
        if not 2 <= base <= 36:
            raise _err("base2dec: base must be between 2 and 36 or a character vector of digits.", "MATLAB:base2dec:InvalidBase")
        lut = {ch: i for i, ch in enumerate("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")}
    rows = [x.text for x in _cellstrs(args[0])] if _is_cell(args[0]) else list(args[0].rows)
    out = []
    for r in rows:
        v = 0.0
        for ch in r.strip() if not _is_text(b) else r:
            if ch == " ":
                continue
            d = lut.get(ch.upper() if not _is_text(b) else ch)
            if d is None or d >= base:
                raise _err(f"base2dec: '{r}' contains digits that are invalid for base {base}.", "MATLAB:base2dec:InvalidDigits")
            v = v * base + d
        out.append(v)
    return (NDArrayValue(np.array(out, dtype=float).reshape(-1, 1)),)


def _strjust(args, *, nargout=1):
    _need(args, 1, "strjust")
    mode = args[1].text.lower() if len(args) > 1 else "right"
    if mode not in ("left", "right", "center"):
        raise _err("strjust: justification must be 'left', 'right' or 'center'.", "MATLAB:strjust:InvalidMode")
    from openmatlab.runtime.char_value import CharValue

    out = []
    for r in args[0].rows:
        t = r.strip(" ")
        n, k = len(r), len(r) - len(r.strip(" "))
        if mode == "left":
            out.append(t + " " * k)
        elif mode == "right":
            out.append(" " * k + t)
        else:
            lft = k // 2
            out.append(" " * lft + t + " " * (k - lft))
        assert len(out[-1]) == n
    return (CharValue(rows=out),)


def _validatestring(args, *, nargout=1):
    _need(args, 2, "validatestring")
    s = args[0]
    if not _is_text(s):
        raise _err("validatestring: expected input to be a character vector or string scalar.", "MATLAB:validatestring:invalidStringType")
    opts = [x.text for x in _cellstrs(args[1])]
    t = s.text.lower()
    exact = [o for o in opts if o.lower() == t]
    if exact:
        return (_cv(exact[0]),)
    hits = [o for o in opts if o.lower().startswith(t)] if t else []
    if len(hits) == 1 or (hits and all(h.lower().startswith(min(hits, key=len).lower()) for h in hits)):
        return (_cv(min(hits, key=len)),)
    if not hits:
        raise _err(f"Expected input to match one of these values:\n\n{', '.join(repr(o) for o in opts)}\n\n"
                   f"The input, '{s.text}', did not match any of the valid values.", "MATLAB:unrecognizedStringChoice")
    raise _err(f"Expected input to match one of these values:\n\n{', '.join(repr(o) for o in opts)}\n\n"
               f"The input, '{s.text}', matched more than one valid value.", "MATLAB:ambiguousStringChoice")


def _getenv(args, *, nargout=1):
    if not args:
        raise _err("getenv: listing all variables is not supported; pass a variable name.", "MATLAB:getenv:NotSupported")
    return (_cv(os.environ.get(args[0].text, "")),)


def _vectorize(args, *, nargout=1):
    _need(args, 1, "vectorize")
    v = args[0]
    if not _is_text(v):
        fh = getattr(v, "source_text", None) or str(getattr(v, "text", "")) or None
        if fh is None:
            raise _err("vectorize: input must be a character vector or an anonymous function.", "MATLAB:vectorize:InvalidInput")
        v = _cv(fh)
    s = v.text
    out, i = [], 0
    while i < len(s):
        ch = s[i]
        if ch in "*/^" and not (i > 0 and s[i - 1] == "."):
            out.append("." + ch)
        else:
            out.append(ch)
        i += 1
    return (_cv("".join(out)),)


# ---- arrays / matrices ------------------------------------------------------------------
def _repelem(args, *, nargout=1):
    _need(args, 2, "repelem")
    v = args[0]
    is_char = _is_text(v)
    a = np.array([list(r) for r in v.rows]) if is_char else _num(v, "repelem")
    if is_char and not v.rows:
        a = np.zeros((0, 0), dtype="<U1")
    reps = [_num(r, "repelem").reshape(-1) for r in args[1:]]
    if len(reps) == 1:
        r = reps[0]
        if not (a.ndim == 2 and 1 in a.shape):
            raise _err("repelem: the input must be a vector when only one repetition argument is given.", "MATLAB:repelem:invalidInput")
        flat = a.reshape(-1)
        if r.size not in (1, flat.size):
            raise _err("repelem: repetition vector length must match the input length.", "MATLAB:repelem:mismatchedReplications")
        rr = np.broadcast_to(r, flat.shape).astype(int)
        if np.any(rr < 0):
            raise _err("repelem: repetition counts must be nonnegative integers.", "MATLAB:repelem:invalidReplications")
        out = np.repeat(flat, rr)
        out = out.reshape(1, -1) if a.shape[0] == 1 else out.reshape(-1, 1)
    else:
        out = a
        for ax, r in enumerate(reps[:2]):
            n = out.shape[ax]
            if r.size not in (1, n):
                raise _err("repelem: repetition vector length must match the input size.", "MATLAB:repelem:mismatchedReplications")
            out = np.repeat(out, np.broadcast_to(r, (n,)).astype(int), axis=ax)
    if is_char:
        from openmatlab.runtime.char_value import CharValue

        return (CharValue(rows=["".join(row) for row in out]),)
    return (NDArrayValue(out),)


def _rref(args, *, nargout=1):
    _need(args, 1, "rref")
    A = _num(args[0], "rref").astype(np.complex128 if np.iscomplexobj(_num(args[0], "rref")) else float).copy()
    m, n = A.shape
    tol = float(_scalar(args[1], "rref")) if len(args) > 1 else max(m, n) * np.finfo(float).eps * (np.linalg.norm(A, np.inf) if A.size else 0.0)
    piv = []
    r = 0
    for c in range(n):
        if r >= m:
            break
        k = int(np.argmax(np.abs(A[r:, c]))) + r
        if abs(A[k, c]) <= tol:
            A[r:, c] = 0
            continue
        piv.append(c + 1)
        A[[r, k]] = A[[k, r]]
        A[r] = A[r] / A[r, c]
        for i in range(m):
            if i != r:
                A[i] = A[i] - A[i, c] * A[r]
        r += 1
    return (_out(A), NDArrayValue(np.array([piv], dtype=float).reshape(1, -1)))[:max(nargout, 1)]


def _pascal(args, *, nargout=1):
    _need(args, 1, "pascal")
    n = int(_scalar(args[0], "pascal"))
    k = int(_scalar(args[1], "pascal")) if len(args) > 1 else 0
    P = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            P[i, j] = math.comb(i + j, i)
    if k == 1 or k == 2:
        L = np.zeros((n, n))
        for i in range(n):
            for j in range(i + 1):
                L[i, j] = math.comb(i, j) * (-1) ** j
        P = L
        if k == 2:
            P = np.rot90(L, 3)
            if n % 2 == 0:
                P = -P
    elif k != 0:
        raise _err("pascal: K must be 0, 1 or 2.", "MATLAB:pascal:InvalidK")
    return (NDArrayValue(P),)



def _spiral(args, *, nargout=1):
    """spiral(n): n-by-n matrix with 1..n^2 in a rectangular spiral (MATLAB demos).

    Public docs: https://www.mathworks.com/help/matlab/ref/spiral.html
    Pattern confirmed against MathWorks Answers spiral(5) listing (Ulam-style).
    """
    _need(args, 1, "spiral")
    n = int(_scalar(args[0], "spiral"))
    if n < 0:
        raise _err("spiral: N must be a non-negative integer.", "MATLAB:spiral:invalidN")
    S = np.zeros((0, 0), dtype=float)
    for m in range(1, n + 1):
        S = np.rot90(S, 2)
        S2 = np.zeros((m, m), dtype=float)
        if m > 1:
            S2[: m - 1, : m - 1] = S
        p = m * m - m + 1
        v = np.arange(m - 1, -1, -1, dtype=float)
        S2[:, m - 1] = p - v
        S2[m - 1, :] = p + v
        S = S2
    if n % 2 == 1:
        S = np.rot90(S, 2)
    return (NDArrayValue(S),)


def _hankel(args, *, nargout=1):
    _need(args, 1, "hankel")
    c = _num(args[0], "hankel").reshape(-1, order="F")
    r = _num(args[1], "hankel").reshape(-1, order="F") if len(args) > 1 else np.zeros(c.size, dtype=c.dtype)
    m, n = c.size, r.size
    out = np.empty((m, n), dtype=np.result_type(c, r, float))
    for i in range(m):
        for j in range(n):
            k = i + j
            out[i, j] = c[k] if k < m else r[k - m + 1]
    return (_out(out),)


def _hadamard(args, *, nargout=1):
    _need(args, 1, "hadamard")
    n = int(_scalar(args[0], "hadamard"))
    if n < 1 or n & (n - 1):
        raise _err("hadamard: N must be a power of 2 (the n/12, n/20 forms are not supported).", "MATLAB:hadamard:InvalidInput")
    H = np.array([[1.0]])
    while H.shape[0] < n:
        H = np.block([[H, H], [H, -H]])
    return (NDArrayValue(H),)


def _vander(args, *, nargout=1):
    _need(args, 1, "vander")
    c = _num(args[0], "vander").reshape(-1, order="F")
    n = int(_scalar(args[1], "vander")) if len(args) > 1 else c.size
    return (_out(np.vander(c, n)),)


def _hilb(args, *, nargout=1):
    n = int(_scalar(args[0], "hilb")) if args else 0
    i = np.arange(1, n + 1.0)
    return (NDArrayValue(1.0 / (i.reshape(-1, 1) + i - 1)),)


def _invhilb(args, *, nargout=1):
    n = int(_scalar(args[0], "invhilb")) if args else 0
    H = np.zeros((n, n))
    for i in range(1, n + 1):
        for j in range(1, n + 1):
            H[i - 1, j - 1] = ((-1) ** (i + j) * (i + j - 1) * math.comb(n + i - 1, n - j) * math.comb(n + j - 1, n - i)
                               * math.comb(i + j - 2, i - 1) ** 2)
    return (NDArrayValue(H),)


def _rosser(args, *, nargout=1):
    R = np.array([[611, 196, -192, 407, -8, -52, -49, 29], [196, 899, 113, -192, -71, -43, -8, -44],
                  [-192, 113, 899, 196, 61, 49, 8, 52], [407, -192, 196, 611, 8, 44, 59, -23],
                  [-8, -71, 61, 8, 411, -599, 208, 208], [-52, -43, 49, 44, -599, 411, 208, 208],
                  [-49, -8, 8, 59, 208, 208, 99, -911], [29, -44, 52, -23, 208, 208, -911, 99]], dtype=float)
    return (NDArrayValue(R),)


def _wilkinson(args, *, nargout=1):
    n = int(_scalar(args[0], "wilkinson")) if args else 0
    m = (n - 1) / 2
    d = np.abs(np.arange(n) - m)
    W = np.diag(d) + np.diag(np.ones(max(n - 1, 0)), 1) + np.diag(np.ones(max(n - 1, 0)), -1)
    return (NDArrayValue(W.reshape(n, n)),)


def _compan(args, *, nargout=1):
    _need(args, 1, "compan")
    a = _num(args[0], "compan")
    if not (a.ndim == 2 and 1 in a.shape):
        raise _err("compan: input must be a vector.", "MATLAB:compan:NeedVectorInput")
    a = a.reshape(-1)
    n = a.size
    if n <= 1:
        return (NDArrayValue(np.zeros((0, 0))),)
    if a[0] == 0:
        raise _err("compan: the first coefficient must be nonzero.", "MATLAB:compan:ZeroLeadingCoefficient")
    C = np.diag(np.ones(n - 2), -1).astype(a.dtype if np.iscomplexobj(a) else float)
    C[0, :] = -a[1:] / a[0]
    return (_out(C),)


def _polyvalm(args, *, nargout=1):
    _need(args, 2, "polyvalm")
    p = _num(args[0], "polyvalm").reshape(-1)
    X = _num(args[1], "polyvalm")
    if X.shape[0] != X.shape[1]:
        raise _err("polyvalm: matrix must be square.", "MATLAB:polyvalm:InputMustBeSquare")
    Y = np.zeros(X.shape, dtype=np.result_type(p, X, float))
    I = np.eye(X.shape[0])
    for c in p:
        Y = Y @ X + c * I
    return (_out(Y),)


def _gradient(args, *, nargout=1):
    _need(args, 1, "gradient")
    F = _num(args[0], "gradient")
    sp = [_num(a, "gradient").reshape(-1) for a in args[1:]]
    vec = F.ndim == 2 and 1 in F.shape
    def g(a, axis, h):
        n = a.shape[axis]
        if n < 2:
            return np.zeros_like(a, dtype=float)
        if h.size == 1:
            return np.gradient(a, float(h[0]), axis=axis, edge_order=1)
        return np.gradient(a, h.astype(float), axis=axis, edge_order=1)
    if vec:
        f = F.reshape(-1)
        h = sp[0] if sp else np.array([1.0])
        return (NDArrayValue(g(f, 0, h).reshape(F.shape)),)
    hx = sp[0] if sp else np.array([1.0])
    hy = sp[1] if len(sp) > 1 else hx
    gx = g(F, 1, hx)
    gy = g(F, 0, hy)
    return (NDArrayValue(gx), NDArrayValue(gy))[:max(nargout, 1)]


def _del2(args, *, nargout=1):
    _need(args, 1, "del2")
    U = _num(args[0], "del2")
    h = float(_scalar(args[1], "del2")) if len(args) > 1 else 1.0
    vec = 1 in U.shape
    axes = [0] if vec and U.shape[1] == 1 else ([1] if vec else [0, 1])
    L = np.zeros(U.shape)
    for ax in axes:
        u = np.moveaxis(U, ax, 0)
        n = u.shape[0]
        d = np.zeros(u.shape)
        if n >= 3:
            d[1:-1] = (u[2:] - 2 * u[1:-1] + u[:-2]) / h ** 2
            d[0] = 2 * d[1] - d[2]
            d[-1] = 2 * d[-2] - d[-3]
        L += np.moveaxis(d, 0, ax)
    return (NDArrayValue(L / 4.0),)  # MATLAB: L = (u_xx + u_yy) / 4, also for vectors


def _conv2_full(a, b):
    m1, n1 = a.shape
    m2, n2 = b.shape
    out = np.zeros((m1 + m2 - 1, n1 + n2 - 1), dtype=np.result_type(a, b, float))
    for i in range(m2):
        for j in range(n2):
            out[i:i + m1, j:j + n1] += b[i, j] * a
    return out


def _shape_crop(full, a_shape, b_shape, shape):
    if shape == "full":
        return full
    m1, n1 = a_shape
    m2, n2 = b_shape
    if shape == "same":
        r0, c0 = m2 // 2, n2 // 2
        return full[r0:r0 + m1, c0:c0 + n1]
    if shape == "valid":
        return full[m2 - 1:m1, n2 - 1:n1] if m1 >= m2 and n1 >= n2 else np.zeros((max(m1 - m2 + 1, 0), max(n1 - n2 + 1, 0)))
    raise _err("conv2: SHAPE must be 'full', 'same' or 'valid'.", "MATLAB:conv2:unknownShapeParameter")


def _conv2(args, *, nargout=1):
    _need(args, 2, "conv2")
    shape = "full"
    if _is_text(args[-1]):
        shape = args[-1].text.lower()
        args = args[:-1]
    if len(args) == 3:
        u = _num(args[0], "conv2").reshape(-1, 1)
        v = _num(args[1], "conv2").reshape(1, -1)
        a = _num(args[2], "conv2")
        b = u @ v
    else:
        a, b = _num(args[0], "conv2"), _num(args[1], "conv2")
    full = _conv2_full(a, b)
    return (_out(_shape_crop(full, a.shape, b.shape, shape)),)


def _filter2(args, *, nargout=1):
    _need(args, 2, "filter2")
    shape = args[2].text.lower() if len(args) > 2 else "same"
    b, x = _num(args[0], "filter2"), _num(args[1], "filter2")
    full = _conv2_full(x, np.rot90(b, 2))
    return (_out(_shape_crop(full, x.shape, b.shape, shape)),)


def _rat(args, *, nargout=1):
    _need(args, 1, "rat")
    X = _num(args[0], "rat")
    tol = float(_scalar(args[1], "rat")) if len(args) > 1 else None
    N = np.zeros(X.shape)
    D = np.ones(X.shape)
    strs = []
    for idx, x in np.ndenumerate(X):
        x = float(x)
        if not math.isfinite(x):
            N[idx], D[idx] = (math.copysign(1, x), 0) if math.isinf(x) else (0, 0)
            strs.append(str(x))
            continue
        t = tol if tol is not None else 1e-6 * np.linalg.norm(X.reshape(-1), 1)
        # continued fraction expansion until |x - n/d| <= t
        y = x
        terms = []
        p0, p1, q0, q1 = 0, 1, 1, 0
        for _ in range(64):
            a = round(y)
            terms.append(a)
            p0, p1 = p1, a * p1 + p0
            q0, q1 = q1, a * q1 + q0
            if abs(x - p1 / q1) <= t or y == a:
                break
            y = 1.0 / (y - a)
        if q1 < 0:
            p1, q1 = -p1, -q1
        N[idx], D[idx] = p1, q1
        s = str(terms[0]) if terms else "0"
        rest = terms[1:]
        for i, k in enumerate(rest):
            if i == len(rest) - 1:
                s += f" + 1/{k}" if k >= 0 else f" + 1/({k})"
            else:
                s += f" + 1/({k}"
        s += ")" * max(len(rest) - 1, 0)
        strs.append(s)
    if nargout >= 2:
        return (NDArrayValue(N), NDArrayValue(D))
    if X.size == 1:
        return (_cv(strs[0]),)
    w = max(len(s) for s in strs) if strs else 0
    from openmatlab.runtime.char_value import CharValue

    return (CharValue(rows=[s.ljust(w) for s in strs]) if strs else _cv(""),)


def _legendre(args, *, nargout=1):
    _need(args, 2, "legendre")
    n = int(_scalar(args[0], "legendre"))
    if n < 0:
        raise _err("legendre: N must be a nonnegative integer.", "MATLAB:legendre:InvalidN")
    X = _num(args[1], "legendre")
    norm = args[2].text.lower() if len(args) > 2 else "unnorm"
    x = X.reshape(-1, order="F").astype(float)
    out = np.zeros((n + 1, x.size))
    s = np.sqrt(np.maximum(1 - x * x, 0.0))
    for m in range(n + 1):
        # P_m^m with Condon-Shortley phase, then upward recurrence in degree
        pmm = np.ones_like(x)
        fact = 1.0
        for _ in range(m):
            pmm = -pmm * fact * s
            fact += 2.0
        if n == m:
            p = pmm
        else:
            pm1 = x * (2 * m + 1) * pmm
            if n == m + 1:
                p = pm1
            else:
                a, b = pmm, pm1
                for ll in range(m + 2, n + 1):
                    a, b = b, (x * (2 * ll - 1) * b - (ll + m - 1) * a) / (ll - m)
                p = b
        if norm == "sch":
            if m > 0:
                p = p * (-1) ** m * math.sqrt(2 * math.factorial(n - m) / math.factorial(n + m))
        elif norm == "norm":
            p = p * (-1) ** m * math.sqrt((n + 0.5) * math.factorial(n - m) / math.factorial(n + m))
        elif norm != "unnorm":
            raise _err("legendre: normalization must be 'unnorm', 'sch' or 'norm'.", "MATLAB:legendre:InvalidNorm")
        out[m] = p
    if X.size == 1 or (X.ndim == 2 and 1 in X.shape):
        return (NDArrayValue(out),)
    return (NDArrayValue(out.reshape((n + 1,) + X.shape, order="F")),)


# ---- elementary ------------------------------------------------------------------------
def _ew(fn, f, check=None):
    def call(args, *, nargout=1):
        _need(args, 1, fn)
        a = _num(args[0], fn)
        if check is not None:
            check(a)
        with np.errstate(all="ignore"):
            return (_out(f(a)),)
    return call


def _real_check(fn, cond, msg):
    def c(a):
        if np.iscomplexobj(a) or np.any(cond(a)):
            raise _err(f"{fn}: {msg}", f"MATLAB:{fn}:complexResult")
    return c


def _realpow(args, *, nargout=1):
    _need(args, 2, "realpow")
    a, b = _num(args[0], "realpow"), _num(args[1], "realpow")
    with np.errstate(all="ignore"):
        r = np.power(a.astype(complex), b)
    if np.any(np.abs(r.imag) > 0):
        raise _err("Realpow produced complex result.", "MATLAB:realpow:complexResult")
    return (_out(r.real),)


def _erfcx1(x):
    if math.isnan(x):
        return math.nan
    if x < 25:
        return math.exp(x * x) * math.erfc(x)
    # asymptotic series (DLMF 7.12.1)
    s, term = 1.0, 1.0
    for k in range(1, 8):
        term *= -(2 * k - 1) / (2 * x * x)
        s += term
    return s / (x * math.sqrt(math.pi))


def _erfcx(args, *, nargout=1):
    _need(args, 1, "erfcx")
    a = _num(args[0], "erfcx")
    if np.iscomplexobj(a):
        raise _err("erfcx: input must be real.", "MATLAB:erfcx:notFullReal")
    return (_out(np.vectorize(_erfcx1, otypes=[float])(a) if a.size else a.astype(float)),)


d2r = np.pi / 180


def register(builtins: Dict[str, Callable]) -> None:
    table = {
        "strtok": _strtok, "isspace": _isspace, "findstr": _findstr, "strmatch": _strmatch,
        "base2dec": _base2dec, "strjust": _strjust, "validatestring": _validatestring, "getenv": _getenv,
        "vectorize": _vectorize, "repelem": _repelem, "rref": _rref, "pascal": _pascal, "spiral": _spiral, "hankel": _hankel,
        "hadamard": _hadamard, "vander": _vander, "hilb": _hilb, "invhilb": _invhilb, "rosser": _rosser,
        "wilkinson": _wilkinson, "compan": _compan, "polyvalm": _polyvalm, "gradient": _gradient, "del2": _del2,
        "conv2": _conv2, "filter2": _filter2, "rat": _rat, "legendre": _legendre, "erfcx": _erfcx,
        "reallog": _ew("reallog", np.log, _real_check("reallog", lambda a: a < 0, "Reallog produced complex result.")),
        "realsqrt": _ew("realsqrt", np.sqrt, _real_check("realsqrt", lambda a: a < 0, "Realsqrt produced complex result.")),
        "realpow": _realpow,
        "secd": _ew("secd", lambda a: 1 / np.cos(a * d2r)), "cscd": _ew("cscd", lambda a: 1 / np.sin(a * d2r)),
        "cotd": _ew("cotd", lambda a: np.where(np.mod(a, 180) == 90, 0.0, 1 / np.tan(a * d2r))),
        "asecd": _ew("asecd", lambda a: np.degrees(np.arccos(1 / a.astype(complex))) if np.any(np.abs(a) < 1) else np.degrees(np.arccos(1 / a))),
        "acscd": _ew("acscd", lambda a: np.degrees(np.arcsin(1 / a.astype(complex))) if np.any(np.abs(a) < 1) else np.degrees(np.arcsin(1 / a))),
        "acotd": _ew("acotd", lambda a: np.degrees(np.arctan(1 / a))),
        "sech": _ew("sech", lambda a: 1 / np.cosh(a)), "csch": _ew("csch", lambda a: 1 / np.sinh(a)),
        "coth": _ew("coth", lambda a: 1 / np.tanh(a)),
        "asech": _ew("asech", lambda a: np.arccosh(1 / a.astype(complex)) if np.any((a <= 0) | (a > 1)) else np.arccosh(1 / a)),
        "acsch": _ew("acsch", lambda a: np.arcsinh(1 / a)),
        "acoth": _ew("acoth", lambda a: np.arctanh(1 / a.astype(complex)) if np.any(np.abs(a) < 1) else np.arctanh(1 / a)),
    }
    for k, v in table.items():
        builtins.setdefault(k, v)
