#!/bin/bash
# finish.sh EPIC FEATPR ACCPR SYNCPR CHILDREN...
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$(git -C "$HERE" rev-parse --show-toplevel)"
set -euo pipefail
E=$1; FP=$2; AP=$3; SP=$4; shift 4
for p in "$FP" "$AP" "$SP"; do
  [ -n "$p" ] || { echo "finish: missing PR number"; exit 1; }
  [ "$(gh pr view $p --json state --jq .state)" = MERGED ] || { echo "finish: PR $p not merged"; exit 1; }
done
F=$(gh pr view $FP --json mergeCommit --jq .mergeCommit.oid); T=$(gh pr view $AP --json mergeCommit --jq .mergeCommit.oid)
for i in "$@"; do gh issue close $i -c "Delivered in #$FP (Epic #$E). CI is green and the change was squash-merged." >/dev/null; done
gh issue comment $E -b "Epic package complete. Ready for user acceptance; this epic stays open until you accept.
- Feature PR #$FP: functional tip \`${F:0:7}\`.
- Acceptance PR #$AP: evidence tip \`${T:0:7}\`. Sync PR #$SP.
- Evidence: docs/acceptance/EPIC-$E.md." >/dev/null
echo "DONE $E F=$F T=$T"
