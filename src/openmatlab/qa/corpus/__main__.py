"""python -m openmatlab.qa.corpus {build|fetch|check} — corpus maintenance (M12)."""

from __future__ import annotations

import argparse
import collections
import sys


def main(argv=None) -> int:
    from openmatlab.qa.corpus import manifest as M

    ap = argparse.ArgumentParser(prog="python -m openmatlab.qa.corpus")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build", help="re-enumerate every source at its pin and rewrite corpus/manifest.json (network)")
    sub.add_parser("fetch", help="populate the local cache from corpus/manifest.json and verify sha256 (network)")
    sub.add_parser("check", help="licence allow-list + no copyleft bodies in the repo (offline)")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "build":
            m = M.build()
            print(f"wrote {M.save(m)} ({len(m.entries)} entries)")
        elif a.cmd == "fetch":
            bad = M.fetch()
            print(f"cache: {M.cache_dir()}  problems: {len(bad)}")
            for k, v in sorted(bad.items())[:50]:
                print(f"  {k}: {v}")
            return 1 if bad else 0
        else:
            m = M.load()
            probs = M.check_allowlist(m) + [f"copyleft body tracked: {p}" for p in M.scan_repo_for_copyleft_bodies(m)]
            c = collections.Counter((e.source, e.kind) for e in m.entries)
            for (s, k), n in sorted(c.items()):
                print(f"{s:12} {k:13} {n}")
            print(f"runnable: {sum(e.runnable for e in m.entries)}  problems: {len(probs)}")
            for p in probs:
                print("  " + p)
            return 1 if probs else 0
    except RuntimeError as exc:  # network failures: one line, no traceback
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
