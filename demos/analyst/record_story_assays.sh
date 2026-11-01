#!/usr/bin/env bash
# Record or prove the analyst field-assay story. The Workbench driver matches
# the M16 showcase (demos/workbench/record_m17_analyst_showcase.sh + m17_driver.py).
#
#   DISPLAY=:2 ./demos/analyst/record_story_assays.sh
#   ./demos/analyst/record_story_assays.sh --headless
#   DISPLAY=:2 ./demos/analyst/record_story_assays.sh --dry-run
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
exec "$ROOT/demos/workbench/record_m17_analyst_showcase.sh" "$@"
