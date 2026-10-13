#!/bin/bash
# epic_close.sh EPIC FEATPR CHILD... — acceptance -> sync -> finish; every step gated.
set -euo pipefail
E=$1; FP=$2; shift 2
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$(git -C "$HERE" rev-parse --show-toplevel)"
[ "$(gh pr view $FP --json state --jq .state)" = MERGED ] || { echo "GATE: feature PR $FP not merged"; exit 1; }
python "$HERE"/accept.py "${EPIC_CONFIG:-/tmp/c$E.json}"
if grep -q '](0x' docs/acceptance/EPIC-$E.md; then echo "GATE: link-like demo output in package"; exit 1; fi
"$HERE"/ship.sh "docs(acceptance): Epic #$E evidence" "Acceptance package for Epic #$E. Refs #$E"
AP=$(gh pr list --state merged --head docs/$E-acceptance --json number --jq '.[0].number')
[ -n "$AP" ] || { echo "GATE: acceptance PR not merged"; exit 1; }
"$HERE"/sync.sh $E $AP
SP=$(gh pr list --state merged --head docs/$E-sync --json number --jq '.[0].number')
[ -n "$SP" ] || { echo "GATE: sync PR not merged"; exit 1; }
"$HERE"/finish.sh $E $FP $AP $SP "$@"
