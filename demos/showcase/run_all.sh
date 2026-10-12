#!/usr/bin/env bash
# Run showcase demos via openmatlab with clear separators.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
OM="${ROOT}/.venv/bin/openmatlab"
if [[ ! -x "$OM" ]]; then
  OM="$(command -v openmatlab)"
fi
DIR="$ROOT/demos/showcase"

echo ""
echo "========== 01_matrix.m =========="
"$OM" -e "$(cat "${DIR}/01_matrix.m")"

echo ""
echo "========== 02_linspace_plot.m =========="
"$OM" -e "$(cat "${DIR}/02_linspace_plot.m")"

echo ""
echo "========== 03_control.m =========="
# run() avoids control-stmt echo; print finals
"$OM" -e "run(\"${DIR}/03_control.m\"); s
k
label"

echo ""
echo "========== 04_cells_unique.m =========="
"$OM" -e "$(cat "${DIR}/04_cells_unique.m")"

echo ""
echo "========== done =========="
