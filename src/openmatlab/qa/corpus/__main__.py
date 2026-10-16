"""python -m openmatlab.qa.corpus {build|fetch|check|run|report|gate|triage} — corpus maintenance and runs (M12)."""

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
    gp = sub.add_parser("report", help="write docs/corpus/REPORT.md from the results JSON (offline)")
    gp.add_argument("--results", default=None, help="results path (default docs/corpus/results.json)")
    gp.add_argument("--baseline", default=None, help="previous results JSON for the regressions section")
    gp.add_argument("--out", default=None, help="report path (default docs/corpus/REPORT.md)")
    gg = sub.add_parser("gate", help="fail (exit 1) if any entry that passed in the baseline no longer passes")
    gg.add_argument("results", help="new results JSON")
    gg.add_argument("--baseline", default=None, help="baseline results JSON (default docs/corpus/results.json)")
    tp = sub.add_parser("triage", help="list failure groups; --file opens deduplicated `corpus` issues (gh)")
    tp.add_argument("--results", default=None)
    tp.add_argument("--file", action="store_true", help="file new groups as GitHub issues (default: dry run)")
    tp.add_argument("--min", type=int, default=2, help="minimum group size to file (internal-crash always files)")
    tp.add_argument("--limit", type=int, default=50, help="maximum new issues per invocation")
    tp.add_argument("--milestone", default=None)
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
        elif a.cmd in ("report", "gate", "triage"):
            return _offline(a)
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
    except (RuntimeError, OSError, ValueError) as exc:  # network failures: one line, no traceback
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


def _offline(a) -> int:
    from pathlib import Path

    from openmatlab.qa.corpus import report, results, triage

    if a.cmd == "gate":
        new = results.load(Path(a.results)).get("records", [])
        base = results.load(Path(a.baseline) if a.baseline else None).get("records", [])
        reg = report.regressions(new, base)
        print(f"corpus gate: {len(reg)} regression(s) (pass -> fail) over {len(new)} entries")
        for i in reg:
            print(f"  {i}")
        return 1 if reg else 0
    doc = results.load(Path(a.results) if a.results else None)
    recs = doc.get("records", [])
    if a.cmd == "report":
        prev = results.load(Path(a.baseline)).get("records", []) if a.baseline else None
        meta = {k: v for k, v in doc.items() if k != "records"}
        out = Path(a.out) if a.out else report.report_path()
        out.write_text(report.render(recs, previous=prev, meta=meta), encoding="utf-8")
        print(f"wrote {out}")
        return 0
    groups = triage.group(recs)
    done = triage.file_issues(groups, min_count=a.min, limit=a.limit, dry_run=not a.file, milestone=a.milestone)
    for g, num, act in done:
        print(f"{act:10} {('#' + str(num)) if num else '-':>6} {g.count:4}  {g.category}: {g.key[:70]}")
    print(f"{len(groups)} groups; {sum(d[2] == 'filed' for d in done)} filed, "
          f"{sum(d[2] == 'exists' for d in done)} already filed, {sum(d[2] == 'would-file' for d in done)} would be filed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
