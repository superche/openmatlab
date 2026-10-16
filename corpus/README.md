# M12 corpus (metadata only)

- `sources.json`: sources, licences, policies and pins.
- `manifest.json`: one entry per corpus item (id, title, URL, revid/commit, sha256, kind). **No corpus code.**
- Code is fetched at run time into `$OPENMATLAB_CORPUS_CACHE` (default `~/.cache/openmatlab-corpus`) with
  `python -m openmatlab.qa.corpus fetch` and verified against the manifest hashes. GPL/GFDL code (Rosetta Code,
  GNU Octave) must never be committed; `python -m openmatlab.qa.corpus check` (and the M12 C01 conformance test in CI)
  enforces the licence allow-list and scans tracked `.m` files for copies of runtime-only entries.
- `python -m openmatlab.qa.corpus build` re-enumerates every source at its pin (maintainers only).

See `docs/milestones/M12-corpus-gate.md`.
