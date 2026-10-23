#!/usr/bin/env bash
# Record the M13 graphics end-to-end capture (Epics #767–#774 / G09–G10 + G03/G05/G08):
# real tk Workbench window driven by xdotool via demos/workbench/m13_driver.py.
# Output: demos/workbench/showcase_m13_graphics.mp4 (copy also to /workspace/recordings/)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source .venv/bin/activate
export DISPLAY="${DISPLAY:-:2}"
OUT="$ROOT/demos/workbench/showcase_m13_graphics.mp4"
TMP="$(mktemp -d)"
FFPID=""
DRY="${1:-}"
trap 'kill -INT "$FFPID" 2>/dev/null || true; rm -rf "$TMP"' EXIT

xdotool search --name 'Google Chrome' windowminimize %@ 2>/dev/null || true
pkill -f 'xfce4-terminal' 2>/dev/null || true
pkill -f 'm13_driver.py' 2>/dev/null || true
sleep 0.5

if [[ "$DRY" != "--dry-run" ]]; then
  ffmpeg -y -video_size 1920x1200 -framerate 15 -f x11grab -draw_mouse 1 -i "$DISPLAY" \
    -c:v libx264 -pix_fmt yuv420p -preset veryfast -crf 23 \
    "$OUT" </dev/null 2>"$TMP/ffmpeg.log" &
  FFPID=$!
  sleep 0.5
fi

python demos/workbench/m13_driver.py "$TMP/project" | tee "$TMP/timeline.txt"

if [[ "$DRY" != "--dry-run" ]]; then
  sleep 1
  kill -INT "$FFPID"; wait "$FFPID" 2>/dev/null || true; FFPID=""
  ls -la "$OUT"
  ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$OUT"
  mkdir -p /workspace/recordings
  cp -f "$OUT" /workspace/recordings/showcase_m13_graphics.mp4
  echo "copied → /workspace/recordings/showcase_m13_graphics.mp4"
fi
echo "--- timeline ---"
cat "$TMP/timeline.txt"
