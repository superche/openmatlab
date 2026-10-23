#!/usr/bin/env bash
# Record or prove the FD001 story. The Workbench driver matches the M13
# showcase (demos/workbench/record_m14_cmapss_showcase.sh + m14_driver.py).
#
#   DISPLAY=:2 ./demos/cmapss/record_story_fd001.sh
#   ./demos/cmapss/record_story_fd001.sh --headless
#   DISPLAY=:2 ./demos/cmapss/record_story_fd001.sh --dry-run
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
exec "$ROOT/demos/workbench/record_m14_cmapss_showcase.sh" "$@"
