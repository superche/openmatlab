# Epic #762 (M12 C-E2): corpus manifest, runtime fetch, licence allow-list

Milestone: [M12 Real-script compatibility gate](../milestones/M12-corpus-gate.md), criterion C01.

## Design

- `corpus/sources.json` lists sources with licence, policy and pin; `allowed_licenses` maps each licence to `runtime` (fetch only) or `vendor` (may be committed with its licence file).
- `corpus/manifest.json` holds metadata only: id, title, URL, revid/commit, sha256 of the code, whitespace-normalised sha256, kind (`script`, `function`, `selftest`, `octave-tests`, `acid-scene`), cache path, optional driver `call` (`{root}` = source checkout).
- `python -m openmatlab.qa.corpus build` enumerates: every MATLAB block on each page in Rosetta Code's Category:MATLAB (pinned by page revid; via the MediaWiki API); GNU Octave `scripts/<dir>/*.m` files with `%!` tests at commit `5208f34c`; chebfun self-tests (tests/chebtech, trigtech, misc, chebfun; BSD-3 licence text verified); matlab2tikz ACID plot scenes (104) and its sources (parse-only).
- `fetch` restores the cache from the pins (Rosetta by revision id through the API, Octave raw files, GitHub tarballs for BSD sources; tar path traversal and links are skipped) and verifies sha256. A network or HTTP failure raises; it is not recorded as `missing after fetch`. `check` runs offline: allow-list + scan of tracked `.m` files against runtime-only hashes. The M12 C01 conformance test runs the same check in CI. `corpus/cache/` is git-ignored.
- CI does not call rosettacode.org. `actions/cache` restores `rosetta/` under the pin hash (`python -m openmatlab.qa.corpus rosetta-key`). On a miss, `restore-rosetta` downloads the `corpus-rosetta` release asset `rosetta-<hash>.tar.gz` and checks sha256. A miss of both fails with upload instructions. `seed-rosetta` builds that archive from a machine that can reach Rosetta Code. The archive is not committed.
- First build: **1495 entries, 1233 runnable** (rosetta 402 scripts + 247 functions, octave 401, chebfun 326, matlab2tikz 104 scenes + 15 functions).
- No source is vendored: the BSD sources are fetched too, which keeps the repo small. Licensing stays within the approved defaults.

## Adversarial review

| Attack | Result |
|---|---|
| Copyleft text sneaks into the manifest | Only titles/URLs/hashes; unit test asserts no code markers |
| A GPL file committed to the repo | `check` and C01 flag it (whole-file match); partial copies → residual #785 |
| Upstream page edited after pinning | Rosetta fetch uses the pinned revid; hash mismatch is reported per entry |
| Malicious tarball paths | GitHub tarballs skip `..` and links; a Rosetta seed archive that contains them is refused |
| Rosetta blocks `index.php?action=raw` (403) | Local fetch uses the API by revid. GitHub-hosted runners get HTTP 403 from Cloudflare on `api.php` and do not call it; CI restores the pin-hash cache or the release seed and checks sha256 |
| GitHub API rate limit | Only `build` uses the API (one tree call); `fetch` uses raw/codeload |
| Network down | `fetch` raises; the CLI prints one error line, no traceback, and does not relabel the failure as `missing after fetch` |
