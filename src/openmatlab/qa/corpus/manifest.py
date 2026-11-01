"""Corpus manifest, runtime fetch and licence allow-list (M12 C01, Epic #762).

The repository stores only ``corpus/sources.json`` (sources, licences, pins) and
``corpus/manifest.json`` (one entry per runnable or parse-only item: title, URL, revid,
sha256). Code is fetched at run time into a local cache (``$OPENMATLAB_CORPUS_CACHE``,
default ``~/.cache/openmatlab-corpus``) and verified against the manifest hash. GPL/GFDL
code is never written inside the repository.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tarfile
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from openmatlab.qa.paths import repo_root

UA = "openmatlab-corpus/1 (+https://github.com/superche/openmatlab; clean-room compatibility testing)"
KINDS = ("script", "function", "selftest", "octave-tests", "acid-scene")
RUNNABLE_KINDS = ("script", "selftest", "octave-tests", "acid-scene")


def corpus_dir() -> Path:
    return repo_root() / "corpus"


def cache_dir() -> Path:
    return Path(os.environ.get("OPENMATLAB_CORPUS_CACHE") or Path.home() / ".cache" / "openmatlab-corpus")


@dataclass
class Entry:
    id: str
    source: str
    title: str
    url: str
    revid: str
    sha256: str
    license: str
    kind: str
    file: str  # path inside the cache
    call: str = ""  # driver code when the entry is not run as a plain script; {root} = the source checkout in the cache
    runnable: bool = True
    extra: dict = field(default_factory=dict)


@dataclass
class Manifest:
    sources: dict
    allowed: dict
    entries: List[Entry]

    def by_source(self) -> Dict[str, List[Entry]]:
        out: Dict[str, List[Entry]] = {}
        for e in self.entries:
            out.setdefault(e.source, []).append(e)
        return out


def sha256(text: str | bytes) -> str:
    return hashlib.sha256(text.encode("utf-8") if isinstance(text, str) else text).hexdigest()


def load_sources() -> dict:
    return json.loads((corpus_dir() / "sources.json").read_text(encoding="utf-8"))


def load(path: Optional[Path] = None) -> Manifest:
    src = load_sources()
    doc = json.loads((path or corpus_dir() / "manifest.json").read_text(encoding="utf-8"))
    return Manifest(sources=src["sources"], allowed=src["allowed_licenses"], entries=[Entry(**e) for e in doc["entries"]])


def check_allowlist(m: Manifest) -> List[str]:
    """Problems: unknown source, licence not allowed, or a copyleft source marked for vendoring."""
    problems = []
    for name, s in m.sources.items():
        pol = m.allowed.get(s["license"])
        if pol is None:
            problems.append(f"{name}: licence {s['license']} not on the allow-list")
        elif s["policy"] == "vendor" and pol != "vendor":
            problems.append(f"{name}: {s['license']} may only be fetched at run time")
    for e in m.entries:
        s = m.sources.get(e.source)
        if s is None:
            problems.append(f"{e.id}: unknown source {e.source}")
        elif e.license != s["license"]:
            problems.append(f"{e.id}: licence {e.license} differs from source {s['license']}")
        if e.kind not in KINDS:
            problems.append(f"{e.id}: unknown kind {e.kind}")
    return problems


def _tracked_files() -> List[Path]:
    root = repo_root()
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True).stdout
        return [root / p for p in out.decode().split("\0") if p]
    except Exception:
        return [p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts and ".venv" not in p.parts]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def scan_repo_for_copyleft_bodies(m: Optional[Manifest] = None) -> List[str]:
    """Tracked files whose (whitespace-normalised) content equals a runtime-only corpus entry.

    Also flags any tracked file under a ``corpus/cache`` folder. Empty list == clean.
    """
    m = m or load()
    runtime = {e.source for e in m.entries if m.allowed.get(e.license) == "runtime"}
    hashes = {e.extra.get("norm_sha256") for e in m.entries if e.source in runtime} - {None}
    bad = []
    for p in _tracked_files():
        rel = p.relative_to(repo_root()).as_posix()
        if rel.startswith("corpus/cache/"):
            bad.append(rel)
            continue
        if p.suffix != ".m" or not p.is_file():
            continue
        try:
            if sha256(_norm(p.read_text(encoding="utf-8", errors="replace"))) in hashes:
                bad.append(rel)
        except OSError:
            pass
    return bad


# -- network ------------------------------------------------------------------------------------
def _get(url: str, retries: int = 4) -> bytes:
    err: Exception = RuntimeError("no attempt")
    for i in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
                return r.read()
        except Exception as exc:  # network flake: back off
            err = exc
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"fetch failed: {url}: {err}")


_RC_API = "https://rosettacode.org/w/api.php"
_MATLAB_HDR = re.compile(r"^==\s*\{\{header\|(?:MATLAB|MATLAB / Octave|Octave / MATLAB)\}\}.*?(?=^==\s*\{\{header\||\Z)", re.S | re.M | re.I)
_BLOCK = re.compile(r"<(?:syntaxhighlight|lang)\b[^>]*>(.*?)</(?:syntaxhighlight|lang)>", re.S)


def rosetta_blocks(wikitext: str) -> List[str]:
    m = _MATLAB_HDR.search(wikitext)
    return [b.strip("\n") + "\n" for b in _BLOCK.findall(m.group(0))] if m else []


def _kind_of(code: str) -> str:
    body = re.sub(r"(?m)^\s*%.*\n", "", code).lstrip()
    return "function" if body.startswith("function") else "script"


def _rosetta_titles() -> List[str]:
    titles, cont = [], {}
    while True:
        q = {"action": "query", "list": "categorymembers", "cmtitle": "Category:MATLAB", "cmlimit": "500",
             "cmnamespace": "0", "format": "json", **cont}
        d = json.loads(_get(_RC_API + "?" + urllib.parse.urlencode(q)))
        titles += [x["title"] for x in d["query"]["categorymembers"]]
        if "continue" not in d:
            return titles
        cont = d["continue"]


def _rosetta_pages(titles: List[str]) -> Dict[str, tuple]:
    out = {}
    for i in range(0, len(titles), 50):
        q = {"action": "query", "prop": "revisions", "rvprop": "ids|content", "rvslots": "main", "format": "json",
             "formatversion": "2", "titles": "|".join(titles[i:i + 50])}
        d = json.loads(_get(_RC_API + "?" + urllib.parse.urlencode(q)))
        for p in d["query"]["pages"]:
            if p.get("revisions"):
                r = p["revisions"][0]
                out[p["title"]] = (str(r["revid"]), r["slots"]["main"]["content"])
    return out


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")


def _cache_write(rel: str, data: str | bytes) -> None:
    p = cache_dir() / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)


def _gh_tarball(repo: str, sha: str, dest: Path) -> Path:
    root = dest / sha
    if not (root / ".complete").is_file():
        data = _get(f"https://codeload.github.com/{repo}/tar.gz/{sha}")
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
            for mem in tf.getmembers():
                parts = mem.name.split("/", 1)
                if len(parts) < 2 or not (mem.isfile() or mem.isdir()) or ".." in parts[1].split("/"):
                    continue
                target = root / parts[1]
                if mem.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(tf.extractfile(mem).read())
        (root / ".complete").write_text("ok")
    return root


def _entry(source, s, ident, title, url, revid, code, kind, file, call="", runnable=None) -> Entry:
    return Entry(id=ident, source=source, title=title, url=url, revid=revid, sha256=sha256(code), license=s["license"],
                 kind=kind, file=file, call=call, runnable=(kind in RUNNABLE_KINDS) if runnable is None else runnable,
                 extra={"norm_sha256": sha256(_norm(code))})


def build(limit_rosetta: Optional[int] = None) -> Manifest:
    """Maintainer step (network): enumerate every source at its pin and write the cache. Returns the manifest."""
    src = load_sources()
    S = src["sources"]
    entries: List[Entry] = []
    # Rosetta Code: every MATLAB code block on every task page in Category:MATLAB, pinned by revid.
    titles = sorted(_rosetta_titles())[:limit_rosetta]
    for title, (revid, text) in sorted(_rosetta_pages(titles).items()):
        for k, code in enumerate(rosetta_blocks(text), 1):
            ident = f"rosetta/{_slug(title)}/{k}"
            kind = _kind_of(code)
            fname = f"rosetta/{_slug(title)}/b{k}/" + (_fn_name(code) or f"rc_{_slug(title)}_{k}") + ".m"
            _cache_write(fname, code)
            url = f"https://rosettacode.org/w/index.php?oldid={revid}"
            entries.append(_entry("rosetta", S["rosetta"], ident, f"{title} (block {k})", url, revid, code, kind, fname))
    # GPL Octave: files with %!assert/%!test blocks in the selected script folders, pinned by commit.
    o = S["octave"]
    tree = json.loads(_get(f"https://api.github.com/repos/gnu-octave/octave/git/trees/{o['pin']}?recursive=1"))
    for item in sorted(tree["tree"], key=lambda t: t["path"]):
        path = item["path"]
        parts = path.split("/")
        if len(parts) != 3 or parts[0] != "scripts" or parts[1] not in o["dirs"] or not path.endswith(".m"):
            continue
        code = _get(f"https://raw.githubusercontent.com/gnu-octave/octave/{o['pin']}/{path}").decode("utf-8", "replace")
        if not re.search(r"(?m)^%!(assert|test|error)", code):
            continue
        fname = f"octave/{o['pin'][:12]}/{path}"
        _cache_write(fname, code)
        entries.append(_entry("octave", o, f"octave/{parts[1]}/{parts[2][:-2]}", path, f"{o['url']}/blob/{o['pin']}/{path}",
                              o["pin"], code, "octave-tests", fname))
    # chebfun (BSD-3): bundled self-test functions of the core classes.
    c = S["chebfun"]
    root = _gh_tarball("chebfun/chebfun", c["pin"], cache_dir() / "chebfun")
    for sub in ("chebtech", "trigtech", "misc", "chebfun"):
        for p in sorted((root / "tests" / sub).glob("test_*.m")):
            code = p.read_text(encoding="utf-8", errors="replace")
            rel = p.relative_to(root).as_posix()
            entries.append(_entry("chebfun", c, f"chebfun/{sub}/{p.stem}", rel, f"{c['url']}/blob/{c['pin']}/{rel}", c["pin"],
                                  code, "selftest", f"chebfun/{c['pin']}/{rel}",
                                  call=f"addpath('{{root}}'); pass = {p.stem}(); assert(all(pass(:)));"))
    # matlab2tikz (BSD-2): every ACID plot scene, plus parse-only checks of the sources.
    t = S["matlab2tikz"]
    root = _gh_tarball("matlab2tikz/matlab2tikz", t["pin"], cache_dir() / "matlab2tikz")
    acid = (root / "test" / "suites" / "ACID.m").read_text(encoding="utf-8", errors="replace")
    handles = re.findall(r"^\s*@(\w+)\s*,?\s*\.\.\.", acid.split("};")[0], re.M)
    for k, h in enumerate(handles, 1):
        entries.append(_entry("matlab2tikz", t, f"matlab2tikz/ACID/{k:03d}_{h}", f"ACID scene {k}: {h}",
                              f"{t['url']}/blob/{t['pin']}/test/suites/ACID.m", t["pin"], acid + f"\n%scene {k}", "acid-scene",
                              f"matlab2tikz/{t['pin']}/test/suites/ACID.m", call=f"addpath('{{root}}/src'); addpath('{{root}}/test/suites'); status = ACID({k});"))
    for p in sorted((root / "src").rglob("*.m")):
        rel = p.relative_to(root).as_posix()
        code = p.read_text(encoding="utf-8", errors="replace")
        entries.append(_entry("matlab2tikz", t, f"matlab2tikz/{rel[:-2]}", rel, f"{t['url']}/blob/{t['pin']}/{rel}", t["pin"],
                              code, "function", f"matlab2tikz/{t['pin']}/{rel}"))
    return Manifest(sources=S, allowed=src["allowed_licenses"], entries=entries)


def _fn_name(code: str) -> str:
    if _kind_of(code) != "function":
        return ""
    m = re.match(r"\s*function\s+(?:\[[^\]]*\]\s*=\s*|\w+\s*=\s*)?(\w+)", re.sub(r"(?m)^\s*%.*\n", "", code))
    return m.group(1) if m else ""


def save(m: Manifest, path: Optional[Path] = None) -> Path:
    path = path or corpus_dir() / "manifest.json"
    doc = {"_doc": "Generated by `python -m openmatlab.qa.corpus build`. Metadata only: no corpus code is stored here.",
           "entries": [asdict(e) for e in m.entries]}
    path.write_text(json.dumps(doc, indent=0, sort_keys=False) + "\n", encoding="utf-8")
    return path


ROSETTA_RELEASE = "corpus-rosetta"


def rosetta_cache_key(m: Optional[Manifest] = None) -> str:
    """Hash of the pinned Rosetta rows. Cache keys and the seed asset name both use this."""
    m = m or load()
    rows = [f"{e.id}\t{e.revid}\t{e.sha256}\t{e.file}" for e in m.entries if e.source == "rosetta"]
    return sha256("\n".join(rows))


def rosetta_seed_name(m: Optional[Manifest] = None) -> str:
    return f"rosetta-{rosetta_cache_key(m)}.tar.gz"


def seed_upload_commands(name: Optional[str] = None) -> str:
    name = name or rosetta_seed_name()
    return (
        f"gh release upload {ROSETTA_RELEASE} {name} --clobber\n"
        "If that release does not exist yet:\n"
        f"  gh release create {ROSETTA_RELEASE} {name} --title \"Rosetta corpus seed\" "
        "--notes \"Pinned Rosetta entries for CI. Not a git commit.\"\n"
        "Do not commit the tarball."
    )


def seed_instructions(name: Optional[str] = None) -> str:
    name = name or rosetta_seed_name()
    return (
        f"Rosetta cache miss for {name}. "
        "GitHub-hosted runners get HTTP 403 from Rosetta Code's Cloudflare, so CI does not fetch it live. "
        f"The workflow restores actions/cache key rosetta-<pin hash> and, on a miss, downloads release asset "
        f"{ROSETTA_RELEASE}/{name} and checks sha256.\n"
        "From a checkout of this manifest, on a machine that can reach https://rosettacode.org :\n"
        "  python -m openmatlab.qa.corpus seed-rosetta\n"
        f"  {seed_upload_commands(name)}"
    )


def _seed_url(name: str) -> str:
    repo = os.environ.get("GITHUB_REPOSITORY") or "superche/openmatlab"
    return f"https://github.com/{repo}/releases/download/{ROSETTA_RELEASE}/{name}"


def _cached_problem(e: Entry) -> Optional[str]:
    p = cache_dir() / e.file
    if not p.is_file():
        return "missing after fetch"
    code = p.read_text(encoding="utf-8", errors="replace")
    if e.kind == "acid-scene":
        code += "\n%scene " + str(int(e.id.rsplit("/", 1)[1].split("_")[0]))
    if sha256(code) != e.sha256:
        return "sha256 mismatch"
    return None


def _rosetta_problems(m: Manifest) -> Dict[str, str]:
    out = {}
    for e in m.entries:
        if e.source != "rosetta":
            continue
        problem = _cached_problem(e)
        if problem:
            out[e.id] = problem
    return out


def _fetch_rosetta_live(m: Manifest) -> None:
    """Download missing Rosetta pins from the MediaWiki API. HTTP failures raise."""
    need = sorted({e.revid for e in m.entries if e.source == "rosetta" and not (cache_dir() / e.file).is_file()})
    texts: Dict[str, str] = {}
    for i in range(0, len(need), 50):  # the API by revision id (index.php?action=raw rejects scripted clients)
        q = {"action": "query", "prop": "revisions", "rvprop": "ids|content", "rvslots": "main", "format": "json",
             "formatversion": "2", "revids": "|".join(need[i:i + 50])}
        d = json.loads(_get(_RC_API + "?" + urllib.parse.urlencode(q)))
        if "query" not in d:
            raise RuntimeError(f"rosetta API error: {d.get('error', d)}")
        for pg in d["query"].get("pages", []):
            for r in pg.get("revisions", []):
                texts[str(r["revid"])] = r["slots"]["main"]["content"]
    for e in m.entries:
        if e.source != "rosetta" or (cache_dir() / e.file).is_file() or e.revid not in texts:
            continue
        blocks = rosetta_blocks(texts[e.revid])
        k = int(e.id.rsplit("/", 1)[1])
        if k <= len(blocks):
            _cache_write(e.file, blocks[k - 1])


def _write_rosetta_tar(m: Manifest, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(dest, mode="w:gz") as tf:
        for e in m.entries:
            if e.source != "rosetta":
                continue
            tf.add(cache_dir() / e.file, arcname=e.file)


def _extract_rosetta_tar(blob: bytes) -> None:
    root = cache_dir().resolve()
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tf:
        for mem in tf.getmembers():
            if not mem.isfile() or mem.issym() or mem.islnk():
                continue
            rel = mem.name.replace("\\", "/").lstrip("./")
            parts = [p for p in rel.split("/") if p not in ("", ".")]
            rel = "/".join(parts)
            if ".." in parts or not rel.startswith("rosetta/"):
                raise RuntimeError(f"refusing seed path {mem.name}")
            target = (root / rel).resolve()
            if root != target and root not in target.parents:
                raise RuntimeError(f"refusing seed path {mem.name}")
            src = tf.extractfile(mem)
            if src is None:
                raise RuntimeError(f"empty seed member {mem.name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(src.read())


def seed_rosetta(out: Optional[Path] = None) -> Path:
    """Fetch any missing Rosetta pins, check sha256, and write the CI seed archive."""
    m = load()
    if any(e.source == "rosetta" and not (cache_dir() / e.file).is_file() for e in m.entries):
        _fetch_rosetta_live(m)
    problems = _rosetta_problems(m)
    if problems:
        sample = "; ".join(f"{k}: {v}" for k, v in list(problems.items())[:3])
        raise RuntimeError(f"seed refused: {len(problems)} Rosetta entries are not in the cache ({sample})")
    dest = out or Path(rosetta_seed_name(m))
    _write_rosetta_tar(m, dest)
    return dest


def restore_rosetta() -> str:
    """Verify the Rosetta cache, or fill it from the release seed. Does not contact Rosetta Code."""
    m = load()
    name = rosetta_seed_name(m)
    if not _rosetta_problems(m):
        return f"rosetta cache ok ({name})"
    shutil.rmtree(cache_dir() / "rosetta", ignore_errors=True)
    try:
        blob = _get(_seed_url(name), retries=2)
    except RuntimeError as exc:
        raise RuntimeError(seed_instructions(name) + f"\nDownload failed: {exc}") from exc
    try:
        _extract_rosetta_tar(blob)
        problems = _rosetta_problems(m)
        if problems:
            sample = "; ".join(f"{k}: {v}" for k, v in list(problems.items())[:3])
            raise RuntimeError(
                f"Rosetta seed {name} does not match the manifest ({len(problems)} entries; {sample})")
    except Exception:
        shutil.rmtree(cache_dir() / "rosetta", ignore_errors=True)
        raise
    return f"restored {name}"


def fetch(m: Optional[Manifest] = None) -> Dict[str, str]:
    """Populate the cache at the pinned revisions and verify hashes. Returns ``{entry id: problem}``.

    Network and HTTP failures raise. On GitHub Actions, missing Rosetta files raise with seed
    instructions instead of calling rosettacode.org.
    """
    m = m or load()
    problems: Dict[str, str] = {}
    S = m.sources
    _gh_tarball("chebfun/chebfun", S["chebfun"]["pin"], cache_dir() / "chebfun")
    _gh_tarball("matlab2tikz/matlab2tikz", S["matlab2tikz"]["pin"], cache_dir() / "matlab2tikz")
    missing_rosetta = any(e.source == "rosetta" and not (cache_dir() / e.file).is_file() for e in m.entries)
    if missing_rosetta:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            raise RuntimeError(seed_instructions())
        _fetch_rosetta_live(m)
    for e in m.entries:
        if e.source == "octave" and not (cache_dir() / e.file).is_file():
            _cache_write(e.file, _get(f"https://raw.githubusercontent.com/gnu-octave/octave/{e.revid}/{e.title}"))
        problem = _cached_problem(e)
        if problem:
            problems[e.id] = problem
    return problems
