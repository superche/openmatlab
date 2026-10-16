"""python -m openmatlab.qa.corpus {build|fetch|check|run} — corpus maintenance and runs (M12)."""

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
    rp = sub.add_parser("run", help="preprocess, run and classify every cached entry; write the results JSON")
    rp.add_argument("--timeout", type=float, default=20.0)
    rp.add_argument("--jobs", type=int, default=None)
    rp.add_argument("--sample", type=int, default=0, help="run every N-th entry only (PR sample); 0 = full run")
    rp.add_argument("--out", default=None, help="results path (default docs/corpus/results.json)")
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
        elif a.cmd == "run":
            from pathlib import Path

            from openmatlab.qa.corpus import pipeline, results

            m = M.load()
            ids = {e.id for k, e in enumerate(sorted(m.entries, key=lambda e: e.id)) if not a.sample or k % a.sample == 0}
            recs = pipeline.run_corpus(m, ids=ids, timeout=a.timeout, jobs=a.jobs)
            out = results.save(recs, full_run=not a.sample, timeout=a.timeout, dest=Path(a.out) if a.out else None)
            c = collections.Counter(r["category"] for r in recs)
            print(f"wrote {out} ({len(recs)} records)")
            for k, n in c.most_common():
                print(f"  {k:24} {n}")
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
