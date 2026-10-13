#!/bin/bash
# sync.sh EPIC ACC_PR  (run only AFTER the acceptance PR merged)
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$(git -C "$HERE" rev-parse --show-toplevel)"; E=$1; P=$2
git checkout -q main && git pull -q
T=$(gh pr view $P --json mergeCommit --jq .mergeCommit.oid); test -n "$T"
git checkout -qb docs/$E-sync
sed -i "s#| Evidence merge tip | [^|]* | [^|]* |#| Evidence merge tip | \`$T\` | Squash merge of [\#$P](https://github.com/superche/openmatlab/pull/$P); re-run from here or \`main\` |#" docs/acceptance/EPIC-$E.md
grep -q "$T" docs/acceptance/EPIC-$E.md
"$HERE"/ship.sh "docs(acceptance): record Epic #$E evidence tip" "Records the evidence tip (#$P squash). Refs #$E"
