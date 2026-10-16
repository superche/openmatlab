#!/bin/bash
# usage: land.sh PR — sync with main if behind, wait for CI, squash-merge
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$(git -C "$HERE" rev-parse --show-toplevel)"
pr=$1
br=$(gh pr view $pr --json headRefName -q .headRefName)
for attempt in 1 2 3; do
  st=$(gh pr view $pr --json mergeStateStatus -q .mergeStateStatus)
  if [ "$st" = "BEHIND" ] || [ "$st" = "DIRTY" ]; then gh api -X PUT repos/superche/openmatlab/pulls/$pr/update-branch >/dev/null || exit 1; sleep 15; fi
  gh pr checks $pr --watch --interval 10 >/dev/null 2>&1
  if gh pr checks $pr | grep -q fail; then echo "PR $pr CI FAIL"; exit 1; fi
  if gh pr merge $pr --squash --delete-branch >/dev/null 2>&1; then echo "PR $pr merged"; exit 0; fi
  sleep 5
done
echo "PR $pr not merged"; exit 1
