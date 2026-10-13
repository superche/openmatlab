#!/bin/bash
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$(git -C "$HERE" rev-parse --show-toplevel)"
. .venv/bin/activate
pytest -q -m "unit or bdd or conformance" -p no:warnings >/tmp/ship_test.log 2>&1 || { tail -30 /tmp/ship_test.log; echo TESTFAIL; exit 1; }
git add -A; git commit -qm "$1" || true
br=$(git branch --show-current)
git push -q -u origin "$br" 2>&1 | grep -v '^remote:' || true
url=$(gh pr create --title "$1" --body "$2" | tail -1); echo "$url"
"$HERE"/land.sh "${url##*/}"
