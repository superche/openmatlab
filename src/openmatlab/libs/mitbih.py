"""MIT-BIH Arrhythmia record 100 runtime fetch and clean-room reader (M15 B-E1, Epic #1008).

Licence: Open Data Commons Attribution License v1.0 (ODC-By 1.0).
Data DOI: 10.13026/C2F305.
G. B. Moody and R. G. Mark, "The impact of the MIT-BIH Arrhythmia Database",
IEEE Engineering in Medicine and Biology Magazine, 20(3):45-50, 2001.
A. L. Goldberger et al., "PhysioBank, PhysioToolkit, and PhysioNet: Components
of a new research resource for complex physiologic signals", Circulation
101(23):e215-e220, 2000.

Only ``100.hea``, ``100.dat`` and ``100.atr`` are downloaded, from
``https://physionet.org/files/mitdb/1.0.0/``. They live under ``downloads/mitbih/``
(or ``$OPENMATLAB_MITBIH_CACHE``) and are never committed.

The header's ADC resolution is 11 bits. On disk the format code is 212: each
sample is a 12-bit two's-complement value, and each frame packs one sample from
each of the two channels into three bytes. The 12th bit is the sign of that
field. Masking the stored word down to 11 bits would change the amplitude, so
the reader keeps the 12-bit value and converts with the header gain and baseline:

    mV = (adc - baseline) / gain
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from openmatlab.qa.paths import repo_root

_GAIN = re.compile(
    r"^(?P<gain>[+-]?(?:\d+(?:\.\d*)?|\.\d+))"
    r"(?:\((?P<res>\d+)\))?"
    r"(?:/(?P<units>\S+))?$"
)
_FMT = re.compile(r"^(?P<fmt>\d+)(?:x(?P<spf>\d+))?$")


@dataclass(frozen=True)
class SignalSpec:
    filename: str
    fmt: int
    gain: float
    adc_resolution: int
    baseline: int
    initial: int
    checksum: int
    description: str
    units: str


@dataclass(frozen=True)
class Header:
    name: str
    fs: float
    n_samples: int
    signals: tuple[SignalSpec, ...]


@dataclass(frozen=True)
class Annotation:
    """One MIT annotation. ``sample`` is the 0-based WFDB sample index."""

    sample: int
    code: int
    aux: str


@dataclass(frozen=True)
class Record:
    header: Header
    adc: np.ndarray
    sig_mv: np.ndarray
    annotations: tuple[Annotation, ...]


def manifest_path() -> Path:
    return repo_root() / "demos" / "mitbih" / "manifest.json"


def load_manifest() -> dict:
    return json.loads(manifest_path().read_text(encoding="utf-8"))


def cache_dir() -> Path:
    """Directory that holds ``100.hea``, ``100.dat`` and ``100.atr``."""
    override = os.environ.get("OPENMATLAB_MITBIH_CACHE")
    if override:
        return Path(override).expanduser()
    return repo_root() / "downloads" / "mitbih"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_cached(path: Path, spec: dict) -> None:
    """Raise ``RuntimeError`` when ``path`` does not match the manifest entry."""
    size = path.stat().st_size
    if size != int(spec["bytes"]):
        raise RuntimeError(f"{spec['name']} size {size} != manifest {spec['bytes']}")
    digest = sha256_file(path)
    if digest != spec["sha256"]:
        raise RuntimeError(f"{spec['name']} sha256 {digest} != manifest {spec['sha256']}")


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_name(dest.name + ".partial")
    req = urllib.request.Request(url, headers={"User-Agent": "openmatlab-mitbih-fetch"})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp, partial.open("wb") as out:
            shutil.copyfileobj(resp, out, length=1 << 20)
    except Exception:
        partial.unlink(missing_ok=True)
        raise
    partial.replace(dest)


def fetch(dest: Path | None = None) -> Path:
    """Download the three record-100 files when the cache is missing or wrong.

    Returns the directory that contains them. A file whose size and sha256
    already match the manifest is left in place.
    """
    manifest = load_manifest()
    root = dest if dest is not None else cache_dir()
    root.mkdir(parents=True, exist_ok=True)
    base = str(manifest["base_url"])
    if not base.endswith("/"):
        base += "/"
    for spec in manifest["files"]:
        path = root / spec["name"]
        if path.is_file():
            try:
                verify_cached(path, spec)
                continue
            except (RuntimeError, OSError):
                path.unlink(missing_ok=True)
        last: Exception | None = None
        for _ in range(3):
            try:
                _download(base + spec["name"], path)
                verify_cached(path, spec)
                last = None
                break
            except Exception as exc:
                last = exc
                path.unlink(missing_ok=True)
        if last is not None:
            raise RuntimeError(f"mitbih_fetch: could not download {spec['name']}: {last}") from None
    return root


def _signal_from_tokens(tokens: list[str]) -> SignalSpec:
    if len(tokens) < 3:
        raise RuntimeError(f"signal line is too short: {' '.join(tokens)}")
    fmt_m = _FMT.fullmatch(tokens[1])
    if fmt_m is None:
        raise RuntimeError(f"bad format field {tokens[1]!r}")
    fmt = int(fmt_m.group("fmt"))
    spf = int(fmt_m.group("spf") or "1")
    if fmt != 212 or spf != 1:
        raise RuntimeError(f"mitbih reader supports format 212 only, got {tokens[1]}")
    gain_m = _GAIN.fullmatch(tokens[2])
    if gain_m is None:
        raise RuntimeError(f"bad gain field {tokens[2]!r}")
    rest = tokens[3:]
    if gain_m.group("res") is not None:
        resolution = int(gain_m.group("res"))
    else:
        if not rest:
            raise RuntimeError("signal line is missing the ADC resolution")
        resolution = int(rest[0])
        rest = rest[1:]
    if len(rest) < 4:
        raise RuntimeError("signal line is missing baseline, initial value, checksum, or block size")
    block = int(rest[3])
    if block != 0:
        raise RuntimeError("mitbih reader does not support blocked signals")
    description = " ".join(rest[4:]) if len(rest) > 4 else ""
    return SignalSpec(
        filename=tokens[0],
        fmt=fmt,
        gain=float(gain_m.group("gain")),
        adc_resolution=resolution,
        baseline=int(rest[0]),
        initial=int(rest[1]),
        checksum=int(rest[2]),
        description=description,
        units=gain_m.group("units") or "mV",
    )


def parse_header(text: str) -> Header:
    """Parse a single-segment WFDB header. Comment lines (``#``) are skipped."""
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append(stripped)
    if not lines:
        raise RuntimeError("empty WFDB header")
    rec = lines[0].split()
    if len(rec) < 4:
        raise RuntimeError("header record line needs name, nsig, fs, and nsamp")
    nsig = int(rec[1])
    if nsig < 1 or len(lines) < 1 + nsig:
        raise RuntimeError(f"header declares {nsig} signals but does not list them")
    signals = tuple(_signal_from_tokens(lines[1 + i].split()) for i in range(nsig))
    return Header(name=rec[0], fs=float(rec[2]), n_samples=int(rec[3]), signals=signals)


def decode_212(data: bytes, n_samples: int) -> np.ndarray:
    """Decode format 212 into an ``(n_samples, 2)`` int32 ADC array.

    Frame bytes ``b0 b1 b2`` hold sample 0 in ``b0`` and the low nibble of
    ``b1``, and sample 1 in ``b2`` (low 8 bits) and the high nibble of ``b1``
    (high 4 bits). Both are 12-bit two's-complement.
    """
    if n_samples < 1:
        raise RuntimeError(f"format 212 needs a positive sample count, got {n_samples}")
    expect = n_samples * 3
    if len(data) != expect:
        raise RuntimeError(f"format 212 file has {len(data)} bytes, expected {expect}")
    frames = np.frombuffer(data, dtype=np.uint8).reshape(-1, 3)
    b0 = frames[:, 0].astype(np.int32)
    b1 = frames[:, 1].astype(np.int32)
    b2 = frames[:, 2].astype(np.int32)
    s0 = b0 | ((b1 & 0x0F) << 8)
    s1 = b2 | ((b1 & 0xF0) << 4)
    s0 = np.where(s0 >= 2048, s0 - 4096, s0)
    s1 = np.where(s1 >= 2048, s1 - 4096, s1)
    return np.stack((s0, s1), axis=1)


def checksum16(samples: np.ndarray) -> int:
    """16-bit signed checksum: the sum of the samples, wrapped into int16."""
    total = int(np.sum(samples.astype(np.int64), dtype=np.int64)) % 65536
    if total >= 32768:
        total -= 65536
    return int(total)


def to_millivolts(adc: np.ndarray, header: Header) -> np.ndarray:
    """``(adc - baseline) / gain`` for each channel. Gain is ADC units per mV."""
    if adc.shape[1] != len(header.signals):
        raise RuntimeError("ADC column count does not match the header")
    out = np.empty(adc.shape, dtype=np.float64)
    for i, spec in enumerate(header.signals):
        if spec.gain == 0:
            raise RuntimeError(f"{spec.description or spec.filename}: gain is 0")
        out[:, i] = (adc[:, i].astype(np.float64) - float(spec.baseline)) / float(spec.gain)
    return out


def _safe_child(root: Path, name: str) -> Path:
    """Refuse a signal filename that is not a single path segment inside ``root``."""
    if not name or name != Path(name).name or name in (".", ".."):
        raise RuntimeError(f"signal file name {name!r} is not a single path segment")
    path = (root / name).resolve()
    if path.parent != root.resolve():
        raise RuntimeError(f"signal file {name!r} escapes the record directory")
    return path


def read_header_file(directory: Path) -> Header:
    heas = sorted(p for p in directory.glob("*.hea") if p.is_file())
    if len(heas) != 1:
        raise RuntimeError(f"expected one .hea in {directory}, found {len(heas)}")
    return parse_header(heas[0].read_text(encoding="latin-1"))


def read_dat(directory: Path, header: Header) -> np.ndarray:
    """Read the shared format-212 file and check each channel's initial value and checksum."""
    if len(header.signals) != 2:
        raise RuntimeError(f"mitbih reader expects 2 signals, got {len(header.signals)}")
    names = {spec.filename for spec in header.signals}
    if len(names) != 1:
        raise RuntimeError("mitbih reader expects both channels in one format 212 file")
    if header.n_samples < 1:
        raise RuntimeError("header sample count must be positive")
    data = _safe_child(directory, header.signals[0].filename).read_bytes()
    adc = decode_212(data, header.n_samples)
    for i, spec in enumerate(header.signals):
        label = spec.description or spec.filename
        first = int(adc[0, i])
        if first != spec.initial:
            raise RuntimeError(f"{label}: first sample {first} != header initial {spec.initial}")
        got = checksum16(adc[:, i])
        if got != spec.checksum:
            raise RuntimeError(f"{label}: checksum {got} != header {spec.checksum}")
    return adc


def parse_atr(data: bytes) -> list[Annotation]:
    """Parse a MIT-format annotation file.

    Each item is a byte pair. The high 6 bits of the second byte are a code
    and the low 10 bits are a sample delta (first byte, plus the low 2 bits of
    the second). Code 59 adds a signed 32-bit skip from the next two pairs.
    Codes 60–63 attach num, subtype, chan, or an aux string to the annotation
    just read and are not themselves annotations. A 0 pair ends the file.
    Aux text drops the trailing NUL the format uses as a terminator.
    """
    if len(data) % 2:
        raise RuntimeError(f"atr length {len(data)} is odd")
    n = len(data) // 2
    bpi = 0
    sample = 0
    out: list[Annotation] = []

    def at(pair: int, which: int) -> int:
        return data[pair * 2 + which]

    def code_at(pair: int) -> int:
        return at(pair, 1) >> 2

    while bpi < n:
        if at(bpi, 0) == 0 and at(bpi, 1) == 0:
            break
        sample_diff = 0
        while bpi < n and code_at(bpi) == 59:
            if bpi + 2 >= n:
                raise RuntimeError("atr SKIP is truncated")
            skip = (
                (at(bpi + 1, 0) << 16)
                + (at(bpi + 1, 1) << 24)
                + at(bpi + 2, 0)
                + (at(bpi + 2, 1) << 8)
            )
            if skip >= 2**31:
                skip -= 2**32
            sample_diff += skip
            bpi += 3
        if bpi >= n or (at(bpi, 0) == 0 and at(bpi, 1) == 0):
            break
        code = code_at(bpi)
        sample_diff += at(bpi, 0) + 256 * (at(bpi, 1) & 3)
        bpi += 1
        sample += sample_diff
        aux = ""
        while bpi < n and code_at(bpi) > 59:
            nxt = code_at(bpi)
            if nxt == 63:
                aux_len = at(bpi, 0)
                span = (aux_len + 1) // 2
                end = bpi + 1 + span
                if end > n:
                    raise RuntimeError("atr AUX is truncated")
                blob = data[(bpi + 1) * 2 : end * 2]
                if aux_len & 1 and blob:
                    blob = blob[:-1]
                aux = blob[:aux_len].split(b"\x00", 1)[0].decode("latin-1")
                bpi = end
            elif nxt in (60, 61, 62):
                bpi += 1
            else:
                raise RuntimeError(f"atr extra code {nxt} is not supported")
        if code != 0:
            out.append(Annotation(sample, code, aux))
    return out


def load_record(root: Path | None = None) -> Record:
    """Read one format-212 record. ``root`` defaults to :func:`fetch`."""
    directory = root if root is not None else fetch()
    if not directory.is_dir():
        raise RuntimeError(f"mitbih record directory does not exist: {directory}")
    header = read_header_file(directory)
    adc = read_dat(directory, header)
    sig = to_millivolts(adc, header)
    atr = _safe_child(directory, f"{header.name}.atr")
    annotations: tuple[Annotation, ...] = ()
    if atr.is_file():
        annotations = tuple(parse_atr(atr.read_bytes()))
    return Record(header=header, adc=adc, sig_mv=sig, annotations=annotations)


# -- MATLAB callables -----------------------------------------------------------------
def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _is_text(v) -> bool:
    from openmatlab.runtime.char_value import CharValue

    return isinstance(v, CharValue) or (getattr(v, "is_string", False) and v.numel() == 1)


def _text(v, fn: str) -> str:
    from openmatlab.runtime.char_value import CharValue

    if isinstance(v, CharValue):
        return v.text
    if getattr(v, "is_string", False) and v.numel() == 1:
        return str(v.data.flat[0])
    raise _err(f"{fn}: argument must be a character vector or string scalar", "MATLAB:invalidType")


def _struct(rec: Record):
    from openmatlab.numerics.ndarray_value import NDArrayValue
    from openmatlab.runtime.char_value import CharValue
    from openmatlab.runtime.struct_value import StructValue
    from openmatlab.runtime.table_value import cellstr_col, cellstr_row

    def scal(x: float):
        return NDArrayValue(np.array([[float(x)]], dtype=np.float64))

    def row(values) -> NDArrayValue:
        return NDArrayValue(np.asarray(list(values), dtype=np.float64).reshape(1, -1))

    def col(values) -> NDArrayValue:
        return NDArrayValue(np.asarray(list(values), dtype=np.float64).reshape(-1, 1))

    signals = rec.header.signals
    if rec.annotations:
        ann_sample = col(a.sample + 1 for a in rec.annotations)
        ann_code = col(a.code for a in rec.annotations)
        ann_aux = cellstr_col([a.aux for a in rec.annotations])
    else:
        ann_sample = NDArrayValue(np.zeros((0, 1)))
        ann_code = NDArrayValue(np.zeros((0, 1)))
        ann_aux = cellstr_col([])
    return StructValue.scalar(
        [
            ("name", CharValue(rec.header.name)),
            ("fs", scal(rec.header.fs)),
            ("sig", NDArrayValue(np.ascontiguousarray(rec.sig_mv, dtype=np.float64))),
            ("names", cellstr_row([s.description for s in signals])),
            ("units", cellstr_row([s.units for s in signals])),
            ("gain", row(s.gain for s in signals)),
            ("baseline", row(s.baseline for s in signals)),
            ("resolution", row(s.adc_resolution for s in signals)),
            ("ann_sample", ann_sample),
            ("ann_code", ann_code),
            ("ann_aux", ann_aux),
        ]
    )


def _mitbih_fetch(args, *, nargout=1):
    """mitbih_fetch: cache directory of 100.hea, 100.dat and 100.atr (char row)."""
    if args:
        raise _err("Too many input arguments.", "MATLAB:TooManyInputs")
    try:
        path = fetch()
    except Exception as exc:
        raise _err(str(exc), "OpenMATLAB:mitbih:FetchFailed") from None
    from openmatlab.runtime.char_value import CharValue

    return (CharValue(str(path)),)


def _mitbih_load(args, *, nargout=1):
    """mitbih_load: record struct. No argument fetches record 100; one argument is a directory."""
    if len(args) > 1:
        raise _err("Too many input arguments.", "MATLAB:TooManyInputs")
    root: Path | None = None
    if args:
        if not _is_text(args[0]):
            raise _err("mitbih_load: directory must be a character vector or string scalar", "MATLAB:invalidType")
        root = Path(_text(args[0], "mitbih_load"))
    try:
        rec = load_record(root)
    except Exception as exc:
        raise _err(str(exc), "OpenMATLAB:mitbih:BadRecord") from None
    return (_struct(rec),)


def register(builtins) -> None:
    builtins["mitbih_fetch"] = _mitbih_fetch
    builtins["mitbih_load"] = _mitbih_load


def main(argv=None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(prog="python -m openmatlab.libs.mitbih")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch", help="download 100.hea, 100.dat and 100.atr into the cache")
    parser.parse_args(argv)
    try:
        print(fetch())
    except (RuntimeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
