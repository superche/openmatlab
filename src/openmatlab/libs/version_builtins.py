"""Release queries: version, ver, verLessThan, isMATLABReleaseOlderThan, matlabRelease (#766).

openmatlab reports the MATLAB language level it targets (R2024b, 24.2.0) so scripts that
branch on the release take the modern path. Only the ``matlab`` product is known.
"""

from __future__ import annotations

import re
from typing import Callable, Dict

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue

RELEASE = "R2024b"
VERSION = (24, 2, 0)
VERSION_TEXT = "24.2.0 (R2024b)"
_RELEASES = {"R2024b": 0}


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _char(s):
    from openmatlab.runtime.char_value import CharValue

    return CharValue(s)


def _text(v, fn):
    if getattr(v, "is_string", False) and hasattr(v, "data"):
        return str(v.data.flat[0])
    t = getattr(v, "text", None)
    if t is None:
        raise _err(f"{fn}: arguments must be text.", f"MATLAB:{fn}:invalidInput")
    return t


def _bool(b):
    return NDArrayValue(np.array([[bool(b)]]))


def _parse(ver: str):
    parts = ver.strip().split(".")
    if not parts or not all(re.fullmatch(r"\d+", p) for p in parts):
        raise _err("Version must be a character vector of the form major[.minor[.build]].",
                   "MATLAB:verLessThan:badVersion")
    nums = [int(p) for p in parts][:3]
    return tuple(nums + [0] * (3 - len(nums)))


def _verlessthan(args, *, nargout=1):
    if len(args) != 2:
        raise _err("Not enough input arguments." if len(args) < 2 else "Too many input arguments.",
                   "MATLAB:minrhs" if len(args) < 2 else "MATLAB:TooManyInputs")
    tb = _text(args[0], "verLessThan").strip().lower()
    if tb != "matlab":
        raise _err(f"Toolbox '{tb}' not found.", "MATLAB:verLessThan:missingToolbox")
    return (_bool(VERSION < _parse(_text(args[1], "verLessThan"))),)


def _version(args, *, nargout=1):
    if args:
        opt = _text(args[0], "version").lower()
        if opt == "-release":
            return (_char(RELEASE[1:]),)
        if opt == "-date":
            return (_char("Aug 21 2024"),)
        raise _err(f"Unknown option '{opt}'.", "MATLAB:version:invalidInput")
    return (_char(VERSION_TEXT),)


def _ver(args, *, nargout=1):
    rec = {"Name": _char("MATLAB"), "Version": _char("24.2"), "Release": _char(f"({RELEASE})"),
           "Date": _char("21-Aug-2024")}
    if args and _text(args[0], "ver").strip().lower() not in ("matlab", ""):
        if nargout:
            return (_empty_ver(),)
        return ()
    if nargout:
        return (_struct(rec),)
    import sys

    sys.stdout.write(f"MATLAB-compatible language level: Version {VERSION_TEXT} (openmatlab)\n")
    return ()


def _struct(rec):
    from openmatlab.runtime.struct_value import StructValue

    return StructValue((1, 1), tuple(rec), (rec,))


def _empty_ver():
    from openmatlab.runtime.struct_value import StructValue

    return StructValue((0, 0), ("Name", "Version", "Release", "Date"), ())


def _older(args, *, nargout=1):
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    rel = _text(args[0], "isMATLABReleaseOlderThan").strip()
    m = re.fullmatch(r"R(\d{4})([ab])", rel)
    if not m:
        raise _err(f"Invalid release '{rel}'.", "MATLAB:isMATLABReleaseOlderThan:invalidRelease")
    return (_bool((int(m.group(1)), m.group(2)) > (2024, "b")),)


def register(builtins: Dict[str, Callable]) -> None:
    for k, v in {"verlessthan": _verlessthan, "version": _version, "ver": _ver,
                 "ismatlabreleaseolderthan": _older}.items():
        builtins.setdefault(k, v)
