#!/usr/bin/env bash
# Create recommended OpenMATLAB GitHub labels (off-the-shelf Issues).
# Usage: ./scripts/ensure_labels.sh [owner/repo]
set -euo pipefail
REPO="${1:-superche/openmatlab}"

create() {
  local name="$1" color="$2" desc="$3"
  gh label create "$name" --repo "$REPO" --color "$color" --description "$desc" --force >/dev/null
  echo "ok  $name"
}

create "bug" "d73a4a" "Incorrect behavior"
create "gap" "fef2c0" "Missing capability vs feature_map"
create "epic" "5319e7" "Multi-issue capability epic"
create "chore" "cfd3d7" "Tooling docs CI chore"
for L in host lang runtime numerics graphics libs qa docs; do
  create "layer:$L" "0e8a16" "Package $L"
done
echo "Done. List with: gh label list --repo $REPO"
