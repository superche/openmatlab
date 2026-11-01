# M12 corpus (metadata only)

- `sources.json`: sources, licences, policies and pins.
- `manifest.json`: one entry per corpus item (id, title, URL, revid/commit, sha256, kind). **No corpus code.**
- Code is fetched at run time into `$OPENMATLAB_CORPUS_CACHE` (default `~/.cache/openmatlab-corpus`) with
  `python -m openmatlab.qa.corpus fetch` and verified against the manifest hashes. GPL/GFDL code (Rosetta Code,
  GNU Octave) must never be committed; `python -m openmatlab.qa.corpus check` (and the M12 C01 conformance test in CI)
  enforces the licence allow-list and scans tracked `.m` files for copies of runtime-only entries.
- `python -m openmatlab.qa.corpus build` re-enumerates every source at its pin (maintainers only).

## CI seed (Rosetta Code)

GitHub-hosted runners get HTTP 403 from Rosetta Code's Cloudflare, so the corpus workflow does not fetch Rosetta live.
It restores `$OPENMATLAB_CORPUS_CACHE/rosetta` from `actions/cache`, keyed by `python -m openmatlab.qa.corpus rosetta-key`.
On a miss it downloads the release asset `corpus-rosetta/rosetta-<hash>.tar.gz` and checks every file against the manifest sha256.
If both are missing, the job fails with the upload commands below. Octave, chebfun and matlab2tikz still come from GitHub at run time.

When the Rosetta pins change, or the first time the asset is needed, from a checkout of that manifest on a machine that can open
https://rosettacode.org :

```text
python -m openmatlab.qa.corpus seed-rosetta
gh release upload corpus-rosetta rosetta-<hash>.tar.gz --clobber
```

Create the release once if it does not exist yet (`gh release create corpus-rosetta rosetta-<hash>.tar.gz`).
Do not commit the tarball. `check` fails if a Rosetta body lands in git.

See `docs/milestones/M12-corpus-gate.md`.
