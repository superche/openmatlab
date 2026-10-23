#!/usr/bin/env bash
# Record or prove the record-100 story. The Workbench driver matches the M14
# showcase (demos/workbench/record_m15_mitbih_showcase.sh + m15_driver.py).
#
#   DISPLAY=:2 ./demos/mitbih/record_story_record100.sh
#   ./demos/mitbih/record_story_record100.sh --headless
#   DISPLAY=:2 ./demos/mitbih/record_story_record100.sh --dry-run
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
exec "$ROOT/demos/workbench/record_m15_mitbih_showcase.sh" "$@"
