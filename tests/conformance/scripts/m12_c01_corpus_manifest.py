"""M12 C01 - corpus manifest: >=300 runnable entries, >=4 sources, licence/url/revid/sha256, no copyleft bodies in repo."""

from pathlib import Path

from openmatlab.qa.corpus import manifest


def run(tmp: Path) -> dict:
    m = manifest.load()
    entries = [e for e in m.entries if e.runnable]
    return {
        "c1": int(len(entries) >= 300),
        "c2": int(len({e.source for e in m.entries}) >= 4),
        "c3": int(all(e.license and e.url and e.revid and len(e.sha256) == 64 for e in m.entries)),
        "c4": int(manifest.check_allowlist(m) == []),
        "c5": int(manifest.scan_repo_for_copyleft_bodies() == []),
    }
