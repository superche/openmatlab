"""NASA C-MAPSS FD001 runtime fetch (M14 V-E1, Epic #994).

Citation: A. Saxena, K. Goebel, D. Simon, and N. Eklund, "Damage Propagation
Modeling for Aircraft Engine Run-to-Failure Simulation", Proceedings of the
1st International Conference on Prognostics and Health Management (PHM08),
Denver, CO, Oct 2008.

Archive: DOI 10.5281/zenodo.15346912, CC BY 4.0.
https://zenodo.org/records/15346912

The zip and the extracted text live under ``downloads/cmapss/`` (or
``$OPENMATLAB_CMAPSS_CACHE``) and are never committed. Same policy as the
GPL corpus cache: the repository stores the size and sha256 only.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import urllib.request
import zipfile
from pathlib import Path

from openmatlab.qa.paths import repo_root

ZIP_NAME = "CMAPSSData.zip"


def manifest_path() -> Path:
    return repo_root() / "demos" / "cmapss" / "manifest.json"


def load_manifest() -> dict:
    return json.loads(manifest_path().read_text(encoding="utf-8"))


def column_names() -> tuple[str, ...]:
    names = tuple(load_manifest()["columns"])
    if len(names) != 26:
        raise RuntimeError(f"C-MAPSS manifest columns must be 26, got {len(names)}")
    return names


def cache_dir() -> Path:
    """Directory that holds ``CMAPSSData.zip`` and ``fd001/``."""
    override = os.environ.get("OPENMATLAB_CMAPSS_CACHE")
    if override:
        return Path(override).expanduser()
    return repo_root() / "downloads" / "cmapss"


def _zip_path(root: Path) -> Path:
    return root / ZIP_NAME


def _fd001_dir(root: Path) -> Path:
    return root / "fd001"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_zip(path: Path, manifest: dict | None = None) -> None:
    """Raise ``RuntimeError`` when the zip size or sha256 does not match the manifest."""
    meta = manifest if manifest is not None else load_manifest()
    size = path.stat().st_size
    if size != int(meta["bytes"]):
        raise RuntimeError(f"CMAPSSData.zip size {size} != manifest {meta['bytes']}")
    digest = sha256_file(path)
    if digest != meta["sha256"]:
        raise RuntimeError(f"CMAPSSData.zip sha256 {digest} != manifest {meta['sha256']}")


def extract_fd001(zip_path: Path, dest: Path, manifest: dict | None = None) -> None:
    """Extract only the three FD001 text files. Member paths are reduced to basenames."""
    meta = manifest if manifest is not None else load_manifest()
    want = {spec["file"] for spec in meta["fd001"].values()}
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        chosen: dict[str, zipfile.ZipInfo] = {}
        for info in zf.infolist():
            if info.is_dir():
                continue
            # Basename only: a member such as ``../evil.txt`` cannot escape ``dest``.
            name = Path(info.filename).name
            if name in want:
                chosen[name] = info
        missing = want - set(chosen)
        if missing:
            raise RuntimeError(f"CMAPSSData.zip is missing {sorted(missing)}")
        for name, info in chosen.items():
            target = dest / name
            with zf.open(info) as src, target.open("wb") as out:
                shutil.copyfileobj(src, out)
    (dest / ".sha256").write_text(meta["sha256"] + "\n", encoding="utf-8")


def _extracted_ok(dest: Path, manifest: dict) -> bool:
    stamp = dest / ".sha256"
    if not stamp.is_file() or stamp.read_text(encoding="utf-8").strip() != manifest["sha256"]:
        return False
    for spec in manifest["fd001"].values():
        path = dest / spec["file"]
        if not path.is_file() or path.stat().st_size <= 0:
            return False
    return True


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_name(dest.name + ".partial")
    req = urllib.request.Request(url, headers={"User-Agent": "openmatlab-cmapss-fetch"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp, partial.open("wb") as out:
            shutil.copyfileobj(resp, out, length=1 << 20)
    except Exception:
        partial.unlink(missing_ok=True)
        raise
    partial.replace(dest)


def fetch(dest: Path | None = None) -> Path:
    """Download the Zenodo zip when needed, check size and sha256, extract FD001.

    Returns the directory that contains ``train_FD001.txt``, ``test_FD001.txt``
    and ``RUL_FD001.txt``.
    """
    manifest = load_manifest()
    root = dest if dest is not None else cache_dir()
    root.mkdir(parents=True, exist_ok=True)
    zpath = _zip_path(root)
    if zpath.is_file():
        try:
            verify_zip(zpath, manifest)
        except (RuntimeError, OSError):
            zpath.unlink(missing_ok=True)
    if not zpath.is_file():
        last: Exception | None = None
        for _ in range(3):
            try:
                _download(manifest["url"], zpath)
                verify_zip(zpath, manifest)
                last = None
                break
            except Exception as exc:  # network, size, or hash — drop the partial zip and retry
                last = exc
                zpath.unlink(missing_ok=True)
        if last is not None:
            raise RuntimeError(f"cmapss_fetch: could not download CMAPSSData.zip: {last}") from None
    out = _fd001_dir(root)
    if not _extracted_ok(out, manifest):
        extract_fd001(zpath, out, manifest)
    return out


# -- MATLAB callables -----------------------------------------------------------------
def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _cmapss_fetch(args, *, nargout=1):
    """cmapss_fetch: cache dir of the three FD001 text files (char row)."""
    if args:
        raise _err("Too many input arguments.", "MATLAB:TooManyInputs")
    try:
        path = fetch()
    except Exception as exc:
        raise _err(str(exc), "OpenMATLAB:cmapss:FetchFailed") from None
    from openmatlab.runtime.char_value import CharValue

    return (CharValue(str(path)),)


def _cmapss_names(args, *, nargout=1):
    """cmapss_names: 1x26 cellstr of PHM08 column names."""
    if args:
        raise _err("Too many input arguments.", "MATLAB:TooManyInputs")
    from openmatlab.runtime.table_value import cellstr_row

    try:
        names = column_names()
    except Exception as exc:
        raise _err(str(exc), "OpenMATLAB:cmapss:BadManifest") from None
    return (cellstr_row(names),)


def register(builtins) -> None:
    builtins["cmapss_fetch"] = _cmapss_fetch
    builtins["cmapss_names"] = _cmapss_names


def main(argv=None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(prog="python -m openmatlab.libs.cmapss")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch", help="download CMAPSSData.zip, verify sha256, extract FD001")
    parser.parse_args(argv)
    try:
        print(fetch())
    except (RuntimeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
