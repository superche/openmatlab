"""BBBC038 stage1_test runtime fetch (M16 I-E1, Epic #1020).

One zip, from the Broad Bioimage Benchmark Collection:

    https://data.broadinstitute.org/bbbc/BBBC038/stage1_test.zip

Content-Length and file size are 9545388 bytes. The sha256 is pinned in
``demos/bbbc038/manifest.json``. The zip and the extracted FOV live under
``downloads/bbbc038/`` (or ``$OPENMATLAB_BBBC038_CACHE``) and are never
committed.

Licence: CC0 1.0. Cite J. C. Caicedo et al., Nature Methods 16:1247-1253,
2019, doi:10.1038/s41592-019-0612-7, and BBBC038v1
(https://bbbc.broadinstitute.org/BBBC038).

The reader extracts one FOV. The zip member name is taken from the manifest
and is not used as a filesystem path, so a ``../`` member cannot leave the
cache directory.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from openmatlab.qa.paths import repo_root

ZIP_NAME = "stage1_test.zip"


@dataclass(frozen=True)
class Cache:
    root: Path
    zip_path: Path
    nbytes: int
    image: Path


def manifest_path() -> Path:
    return repo_root() / "demos" / "bbbc038" / "manifest.json"


def load_manifest() -> dict:
    return json.loads(manifest_path().read_text(encoding="utf-8"))


def cache_dir() -> Path:
    """Directory that holds ``stage1_test.zip`` and ``fov/``."""
    override = os.environ.get("OPENMATLAB_BBBC038_CACHE")
    if override:
        return Path(override).expanduser()
    return repo_root() / "downloads" / "bbbc038"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def member_ok(name: str) -> bool:
    """True when ``name`` is a relative zip path with no empty, ``.``, or ``..`` segment."""
    if not name or name.startswith("/") or "\\" in name:
        return False
    parts = name.split("/")
    return all(part not in ("", ".", "..") for part in parts)


def check_content_length(value: str | None, expected: int) -> None:
    """Raise when a Content-Length header is present and is not ``expected``."""
    if value is None or value == "":
        return
    try:
        got = int(value)
    except ValueError as exc:
        raise RuntimeError(f"Content-Length {value!r} is not an integer") from exc
    if got != expected:
        raise RuntimeError(f"Content-Length {got} != manifest {expected}")


def verify_cached(path: Path, spec: dict) -> None:
    """Raise ``RuntimeError`` when ``path`` does not match ``spec`` size and sha256."""
    label = spec.get("name") or path.name
    size = path.stat().st_size
    if size != int(spec["bytes"]):
        raise RuntimeError(f"{label} size {size} != manifest {spec['bytes']}")
    digest = sha256_file(path)
    if digest != spec["sha256"]:
        raise RuntimeError(f"{label} sha256 {digest} != manifest {spec['sha256']}")


def verify_zip(path: Path, manifest: dict | None = None) -> None:
    meta = manifest if manifest is not None else load_manifest()
    verify_cached(path, {"name": ZIP_NAME, "bytes": meta["bytes"], "sha256": meta["sha256"]})


def extract_fov(zip_path: Path, dest: Path, fov: dict) -> None:
    """Write the one manifest FOV to ``dest``. The member name is not a path."""
    member = str(fov["member"])
    if not member_ok(member):
        raise RuntimeError(f"FOV member is not a safe zip path: {member}")
    with zipfile.ZipFile(zip_path) as zf:
        info = next((item for item in zf.infolist() if item.filename == member), None)
        if info is None or info.is_dir():
            raise RuntimeError(f"stage1_test.zip has no FOV member {member}")
        data = zf.read(info)
    if len(data) != int(fov["bytes"]):
        raise RuntimeError(f"FOV size {len(data)} != manifest {fov['bytes']}")
    digest = hashlib.sha256(data).hexdigest()
    if digest != fov["sha256"]:
        raise RuntimeError(f"FOV sha256 {digest} != manifest {fov['sha256']}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_name(dest.name + ".partial")
    partial.write_bytes(data)
    partial.replace(dest)


def _download(url: str, dest: Path, expected_bytes: int) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_name(dest.name + ".partial")
    req = urllib.request.Request(url, headers={"User-Agent": "openmatlab-bbbc038-fetch"})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp, partial.open("wb") as out:
            check_content_length(resp.headers.get("Content-Length"), expected_bytes)
            shutil.copyfileobj(resp, out, length=1 << 20)
    except Exception:
        partial.unlink(missing_ok=True)
        raise
    partial.replace(dest)


def fetch(dest: Path | None = None) -> Cache:
    """Download ``stage1_test.zip`` when needed, check it, and extract one FOV.

    A zip whose size and sha256 already match is not downloaded again. The
    returned image path is ``<cache>/fov/<basename>.png``.
    """
    manifest = load_manifest()
    root = dest if dest is not None else cache_dir()
    root.mkdir(parents=True, exist_ok=True)
    zpath = root / ZIP_NAME
    if zpath.is_file():
        try:
            verify_zip(zpath, manifest)
        except (RuntimeError, OSError):
            zpath.unlink(missing_ok=True)
    if not zpath.is_file():
        last: Exception | None = None
        for _ in range(3):
            try:
                _download(manifest["url"], zpath, int(manifest["bytes"]))
                verify_zip(zpath, manifest)
                last = None
                break
            except Exception as exc:
                last = exc
                zpath.unlink(missing_ok=True)
        if last is not None:
            raise RuntimeError(f"bbbc038_fetch: could not download stage1_test.zip: {last}") from None
    fov = manifest["fov"]
    image = root / "fov" / Path(fov["member"]).name
    if not member_ok(str(fov["member"])):
        raise RuntimeError(f"FOV member is not a safe zip path: {fov['member']}")
    if image.is_file():
        try:
            verify_cached(image, {"name": image.name, "bytes": fov["bytes"], "sha256": fov["sha256"]})
        except (RuntimeError, OSError):
            image.unlink(missing_ok=True)
    if not image.is_file():
        extract_fov(zpath, image, fov)
    return Cache(root=root, zip_path=zpath, nbytes=zpath.stat().st_size, image=image)


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _struct(cache: Cache):
    from openmatlab.numerics.ndarray_value import NDArrayValue
    from openmatlab.runtime.char_value import CharValue
    from openmatlab.runtime.struct_value import StructValue

    return StructValue.scalar(
        [
            ("zip", CharValue(str(cache.zip_path))),
            ("bytes", NDArrayValue(np.array([[float(cache.nbytes)]], dtype=np.float64))),
            ("image", CharValue(str(cache.image))),
        ]
    )


def _bbbc038_fetch(args, *, nargout=1):
    """bbbc038_fetch: struct with zip path, byte size, and the extracted FOV path."""
    if args:
        raise _err("Too many input arguments.", "MATLAB:TooManyInputs")
    try:
        cache = fetch()
    except Exception as exc:
        raise _err(str(exc), "OpenMATLAB:bbbc038:FetchFailed") from None
    return (_struct(cache),)


def register(builtins) -> None:
    builtins["bbbc038_fetch"] = _bbbc038_fetch


def main(argv=None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(prog="python -m openmatlab.libs.bbbc038")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch", help="download stage1_test.zip and extract one FOV")
    parser.parse_args(argv)
    try:
        print(fetch().root)
    except (RuntimeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
