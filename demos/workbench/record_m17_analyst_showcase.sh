#!/usr/bin/env bash
# Record the M17 analyst story in the real tk Workbench (issue #1034).
# Driver: demos/workbench/m17_driver.py
# Output: demos/workbench/showcase_m17_analyst.mp4
#
# Same display convention as the M16 showcase:
#   DISPLAY=:2 ./demos/workbench/record_m17_analyst_showcase.sh
# GUI without ffmpeg:
#   DISPLAY=:2 ./demos/workbench/record_m17_analyst_showcase.sh --dry-run
# No display: prove the story and the driver source, write no mp4:
#   ./demos/workbench/record_m17_analyst_showcase.sh --headless
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
if [[ -f "$ROOT/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi
PY=python
if ! command -v python >/dev/null 2>&1; then
  PY=python3
fi
export DISPLAY="${DISPLAY:-:2}"
OUT="$ROOT/demos/workbench/showcase_m17_analyst.mp4"
TMP="$(mktemp -d)"
FFPID=""
MODE="${1:-}"
trap 'kill -INT "$FFPID" 2>/dev/null || true; rm -rf "$TMP"' EXIT

headless_proof() {
  echo "M17 headless proof (no mp4; Workbench capture needs a display)"
  bash -n "$ROOT/demos/workbench/record_m17_analyst_showcase.sh"
  bash -n "$ROOT/demos/analyst/record_story_assays.sh"
  "$PY" -c "import ast; from pathlib import Path; ast.parse(Path('demos/workbench/m17_driver.py').read_text())"
  echo "driver parses; record scripts pass bash -n"
  openmatlab -e "run('demos/analyst/story_assays.m')"
  git check-ignore -v demos/analyst/out/site_summary.csv demos/analyst/out/cleaned.csv
  git check-ignore -q demos/analyst/out/README.md && echo "README should not be ignored" && exit 1
  git ls-files demos/analyst/out
  "$PY" - <<'PY'
from pathlib import Path
summary = Path("demos/analyst/out/site_summary.csv")
cleaned = Path("demos/analyst/out/cleaned.csv")
print(f"summary bytes {summary.stat().st_size}")
print(f"cleaned bytes {cleaned.stat().st_size}")
print(summary.read_text().splitlines()[0])
print(summary.read_text().splitlines()[-1])
PY
  echo "headless proof done; no mp4 written"
}

if [[ "$MODE" == "--headless" ]]; then
  headless_proof
  exit 0
fi

if ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
  echo "No X display $DISPLAY. On the capture box: DISPLAY=:2 $0" >&2
  echo "Without a display: $0 --headless" >&2
  exit 2
fi

xdotool search --name 'Google Chrome' windowminimize %@ 2>/dev/null || true
pkill -f 'xfce4-terminal' 2>/dev/null || true
pkill -f 'm17_driver.py' 2>/dev/null || true
sleep 0.5

if [[ "$MODE" != "--dry-run" ]]; then
  ffmpeg -y -video_size 1920x1200 -framerate 15 -f x11grab -draw_mouse 1 -i "$DISPLAY" \
    -c:v libx264 -pix_fmt yuv420p -preset veryfast -crf 23 \
    "$OUT" </dev/null 2>"$TMP/ffmpeg.log" &
  FFPID=$!
  sleep 0.5
fi

"$PY" demos/workbench/m17_driver.py "$ROOT/demos/analyst" | tee "$TMP/timeline.txt"

if [[ "$MODE" != "--dry-run" ]]; then
  sleep 1
  kill -INT "$FFPID"; wait "$FFPID" 2>/dev/null || true; FFPID=""
  ls -la "$OUT"
  ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$OUT"
  REC="/workspace/recordings"
  case "$REC" in
    "$ROOT"|"$ROOT"/*)
      echo "skip in-repo copy of $REC (checkout is $ROOT)"
      ;;
    *)
      mkdir -p "$REC"
      cp -f "$OUT" "$REC/showcase_m17_analyst.mp4"
      echo "copied → $REC/showcase_m17_analyst.mp4"
      ;;
  esac
fi
echo "--- timeline ---"
cat "$TMP/timeline.txt"
