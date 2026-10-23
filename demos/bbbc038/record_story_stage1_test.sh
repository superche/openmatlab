#!/usr/bin/env bash
# Record or prove the BBBC038 stage1_test story. The Workbench driver matches
# the M15 showcase (demos/workbench/record_m16_bbbc038_showcase.sh + m16_driver.py).
#
#   DISPLAY=:2 ./demos/bbbc038/record_story_stage1_test.sh
#   ./demos/bbbc038/record_story_stage1_test.sh --headless
#   DISPLAY=:2 ./demos/bbbc038/record_story_stage1_test.sh --dry-run
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
exec "$ROOT/demos/workbench/record_m16_bbbc038_showcase.sh" "$@"
