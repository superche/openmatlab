#!/usr/bin/env bash
# Record Epic #372 MATLAB-aligned Workbench showcase:
# clear fullscreen terminal (list/eval) + tk Host window walkthrough (W01–W06).
# Output: demos/workbench/showcase_workbench.mp4
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source .venv/bin/activate
export DISPLAY="${DISPLAY:-:2}"
OUT="$ROOT/demos/workbench/showcase_workbench.mp4"
DEMO_DIR="$ROOT/demos/workbench/sample_project"
TMP="$(mktemp -d)"
TERM_DONE="$TMP/term_done"
trap 'rm -rf "$TMP"; pkill -f "xfce4-terminal.*OpenMATLAB workbench" 2>/dev/null || true; pkill -f "openmatlab workbench" 2>/dev/null || true; kill "$FFPID" 2>/dev/null || true' EXIT

mkdir -p "$DEMO_DIR"
cat > "$DEMO_DIR/showcase_demo.m" <<'M'
% Epic #372 workbench showcase sample
x = 1:5;
y = x .* x;
M
cat > "$DEMO_DIR/notes.txt" <<'T'
sample project for Current Folder browser
T

# Hide Chrome / other non-showcase windows — clear window
wmctrl -r 'Google Chrome' -b add,hidden 2>/dev/null || true
xdotool search --name 'Google Chrome' windowminimize %@ 2>/dev/null || true
pkill -f 'xfce4-terminal' 2>/dev/null || true
pkill -f 'openmatlab workbench' 2>/dev/null || true
pkill -f 'openmatlab desktop' 2>/dev/null || true
sleep 0.5

cat > "$TMP/term.sh" <<DEMO
#!/usr/bin/env bash
set -e
cd /workspace/openmatlab
source .venv/bin/activate
clear
echo "############################################################"
echo "# OpenMATLAB MATLAB-aligned Workbench showcase"
echo "# Epic #372 · W01–W06 Host panels (CW/Editor/WS/Folder/Figs)"
echo "############################################################"
sleep 1.2

echo
echo "=== 1 Host layout regions (all ready) ==="
echo ">> openmatlab workbench --list-only"
openmatlab workbench --list-only
sleep 2.0

echo
echo "=== 2 Command Window headless eval ==="
echo ">> openmatlab workbench --eval 'a = [1 2 3]; b = a + 1'"
openmatlab workbench --eval 'a = [1 2 3]; b = a + 1'
sleep 1.5

echo
echo "=== 3 Open Host tk workbench (scripted W03–W06 walkthrough) ==="
echo ">> openmatlab workbench --cwd demos/workbench/sample_project --demo-ms 9000"
openmatlab workbench --cwd demos/workbench/sample_project --demo-ms 9000
sleep 0.5

echo
echo "############################################################"
echo "# Epic #372 workbench showcase — DONE (window + panels)"
echo "############################################################"
sleep 2.0
touch "$TERM_DONE"
sleep 3.0
DEMO
chmod +x "$TMP/term.sh"

FFPID=""
ffmpeg -y -video_size 1920x1200 -framerate 12 -f x11grab -i "$DISPLAY" \
  -c:v libx264 -pix_fmt yuv420p -preset ultrafast -crf 26 \
  "$OUT" </dev/null 2>"$TMP/ffmpeg.log" &
FFPID=$!
sleep 0.5

xfce4-terminal \
  --disable-server \
  --fullscreen \
  --title="OpenMATLAB workbench showcase" \
  --hide-menubar \
  --hide-toolbar \
  --hide-scrollbar \
  --font='DejaVu Sans Mono 20' \
  -e "bash $TMP/term.sh" &
TERM_PID=$!

for _ in $(seq 1 240); do
  if [[ -f "$TERM_DONE" ]]; then
    break
  fi
  sleep 0.25
done
if [[ ! -f "$TERM_DONE" ]]; then
  echo "ERROR: terminal phase did not signal done" >&2
  kill "$FFPID" 2>/dev/null || true
  exit 1
fi
sleep 2.5
kill -INT "$FFPID" 2>/dev/null || true
wait "$FFPID" 2>/dev/null || true
FFPID=""
sleep 0.2
pkill -f 'xfce4-terminal' 2>/dev/null || true
wait "$TERM_PID" 2>/dev/null || true

ls -la "$OUT"
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$OUT" || true
