"""FFT family (M3 E1, #625): fft/ifft/fft2/ifft2/fftn/ifftn/fftshift/ifftshift/nextpow2.

MATLAB semantics: ``fft(X, n, dim)`` operates along the first non-singleton
dimension by default, zero-pads or truncates to ``n``; ``[]`` for ``n`` means
"keep size".  ``ifft(..., 'symmetric')`` returns the real part.
"""

from __future__ import annotations

from typing import Callable, Dict

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _arr(v):
    a = np.asarray(v.backend_buffer())
    if a.dtype == bool:
        a = a.astype(float)
    return a


def _is_text(v, word):
    t = getattr(v, "text", None)
    return isinstance(t, str) and t.lower() == word


def _first_ns(a):
    for i, s in enumerate(a.shape):
        if s != 1:
            return i
    return 0


def _intarg(v, what):
    a = np.asarray(v.backend_buffer()).reshape(-1)
    if a.size != 1 or a[0] != np.floor(a[0]) or a[0] < (1 if what == "dim" else 0):
        if what == "dim":
            raise _err("Dimension argument must be a positive integer scalar within indexing range.", "MATLAB:getdimarg:dimensionMustBePositiveInteger")
        raise _err("N-point FFT must be a nonnegative integer scalar.", "MATLAB:fftfcn:lengthNotNonnegInt")
    return int(a[0])


def _pack(r, symmetric=False):
    if symmetric or np.isrealobj(r):
        r = np.real(r).astype(float)
    return NDArrayValue(np.asarray(r))


def _fft1(name, inverse):
    def fn(args, *, nargout=1):
        args = list(args)
        sym = False
        if args and _is_text(args[-1], "symmetric") and inverse:
            sym = True
            args.pop()
        elif args and _is_text(args[-1], "nonsymmetric") and inverse:
            args.pop()
        if not 1 <= len(args) <= 3:
            raise _err(f"Incorrect number of input arguments for {name}.", "MATLAB:narginchk:notEnoughInputs")
        a = _arr(args[0])
        dim = _intarg(args[2], "dim") - 1 if len(args) > 2 else _first_ns(a)
        n = None
        if len(args) > 1 and np.asarray(args[1].backend_buffer()).size:
            n = _intarg(args[1], "n")
        if a.size == 0 and n is None:
            return [NDArrayValue(a.astype(float))]
        while a.ndim <= dim:
            a = a[..., None]
        if n is None:
            n = a.shape[dim]
        if n == 0:
            shp = list(a.shape)
            shp[dim] = 0
            return [NDArrayValue(np.zeros(shp))]
        f = np.fft.ifft if inverse else np.fft.fft
        r = f(a, n=n, axis=dim)
        if not inverse and np.isrealobj(a):
            r = r.astype(complex)
        return [_pack(r, sym) if inverse else NDArrayValue(r)]

    return fn


def _fft2(name, inverse, nd):
    def fn(args, *, nargout=1):
        args = list(args)
        sym = bool(args) and inverse and _is_text(args[-1], "symmetric")
        if sym:
            args.pop()
        a = _arr(args[0])
        f = (np.fft.ifftn if inverse else np.fft.fftn)
        if nd:
            s = None
            if len(args) > 1:
                s = [int(x) for x in np.asarray(args[1].backend_buffer()).reshape(-1)]
                while a.ndim < len(s):
                    a = a[..., None]
            r = f(a, s=s, axes=None if s is None else list(range(len(s))))
        else:
            s = None
            if len(args) == 3:
                s = [_intarg(args[1], "n"), _intarg(args[2], "n")]
            elif len(args) == 2:
                s = [int(x) for x in np.asarray(args[1].backend_buffer()).reshape(-1)][:2]
            r = f(a, s=s, axes=(0, 1))
        if not inverse:
            return [NDArrayValue(np.asarray(r).astype(complex))]
        return [_pack(r, sym)]

    return fn


def _shift(inverse):
    def fn(args, *, nargout=1):
        a = np.asarray(args[0].backend_buffer())
        axes = None
        if len(args) > 1:
            axes = _intarg(args[1], "dim") - 1
            if axes >= a.ndim:
                return [args[0]]
        r = np.fft.ifftshift(a, axes=axes) if inverse else np.fft.fftshift(a, axes=axes)
        return [NDArrayValue(r) if not hasattr(args[0], "with_data") else args[0].with_data(r)]

    return fn


def _nextpow2(args, *, nargout=1):
    """Smallest p with 2^p >= abs(x), exact (frexp / integer bit length); class of the input."""
    a = np.asarray(args[0].backend_buffer())
    if a.dtype.kind in "iu":
        r = np.array([(abs(int(v)) - 1).bit_length() if v else 0 for v in a.reshape(-1)], dtype=a.dtype)
        return [NDArrayValue(r.reshape(a.shape))]
    x = np.abs(a.astype(np.float64) if a.dtype.kind in "b" else a)
    m, e = np.frexp(np.where(np.isfinite(x), x, 1))
    r = np.where(m == 0.5, e - 1, e).astype(np.float64)
    r = np.where(x == 0, 0.0, r)
    r = np.where(np.isinf(x), np.inf, np.where(np.isnan(x), np.nan, r))
    return [NDArrayValue(np.asarray(r, dtype=np.float32 if a.dtype in (np.float32, np.complex64) else np.float64))]


def register(builtins: Dict[str, Callable]) -> None:
    builtins["fft"] = _fft1("fft", False)
    builtins["ifft"] = _fft1("ifft", True)
    builtins["fft2"] = _fft2("fft2", False, False)
    builtins["ifft2"] = _fft2("ifft2", True, False)
    builtins["fftn"] = _fft2("fftn", False, True)
    builtins["ifftn"] = _fft2("ifftn", True, True)
    builtins["fftshift"] = _shift(False)
    builtins["ifftshift"] = _shift(True)
    builtins["nextpow2"] = _nextpow2
