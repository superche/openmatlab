#!/usr/bin/env bash
# Record the M11 D10 end-to-end capture (Epic #703 / residual #751):
# real tk Workbench window driven by xdotool via demos/workbench/d10_driver.py.
# Output: demos/workbench/showcase_d10_debugger_workflows.mp4 (copy also to /workspace/recordings/D10-e2e.mp4)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source .venv/bin/activate
export DISPLAY="${DISPLAY:-:2}"
OUT="$ROOT/demos/workbench/showcase_d10_debugger_workflows.mp4"
TMP="$(mktemp -d)"
FFPID=""
trap 'kill -INT "$FFPID" 2>/dev/null || true; rm -rf "$TMP"' EXIT

xdotool search --name 'Google Chrome' windowminimize %@ 2>/dev/null || true
pkill -f 'xfce4-terminal' 2>/dev/null || true
sleep 0.5

ffmpeg -y -video_size 1920x1200 -framerate 15 -f x11grab -draw_mouse 1 -i "$DISPLAY" \
  -c:v libx264 -pix_fmt yuv420p -preset veryfast -crf 23 \
  "$OUT" </dev/null 2>"$TMP/ffmpeg.log" &
FFPID=$!
sleep 0.5
python demos/workbench/d10_driver.py "$TMP/project" | tee "$TMP/timeline.txt"
sleep 1
kill -INT "$FFPID"; wait "$FFPID" 2>/dev/null || true; FFPID=""
ls -la "$OUT"
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$OUT"
