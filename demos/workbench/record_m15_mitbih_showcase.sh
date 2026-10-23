#!/usr/bin/env bash
# Record the M15 MIT-BIH record-100 story in the real tk Workbench (Epic #1013 / V08–V09).
# Driver: demos/workbench/m15_driver.py
# Output: demos/workbench/showcase_m15_mitbih.mp4
#
# Shaw's box (same display as the M14 showcase):
#   DISPLAY=:2 ./demos/workbench/record_m15_mitbih_showcase.sh
# GUI without ffmpeg (M13 --dry-run):
#   DISPLAY=:2 ./demos/workbench/record_m15_mitbih_showcase.sh --dry-run
# No display: prove the story and the driver source, write no mp4:
#   ./demos/workbench/record_m15_mitbih_showcase.sh --headless
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
OUT="$ROOT/demos/workbench/showcase_m15_mitbih.mp4"
TMP="$(mktemp -d)"
FFPID=""
MODE="${1:-}"
trap 'kill -INT "$FFPID" 2>/dev/null || true; rm -rf "$TMP"' EXIT

headless_proof() {
  echo "M15 headless proof (no mp4; Workbench capture needs a display)"
  bash -n "$ROOT/demos/workbench/record_m15_mitbih_showcase.sh"
  bash -n "$ROOT/demos/mitbih/record_story_record100.sh"
  "$PY" -c "import ast; from pathlib import Path; ast.parse(Path('demos/workbench/m15_driver.py').read_text())"
  echo "driver parses; record scripts pass bash -n"
  "$PY" -m openmatlab.libs.mitbih fetch
  openmatlab -e "run('demos/mitbih/story_record100.m')"
  git check-ignore -v downloads/mitbih/100.hea downloads/mitbih/100.dat downloads/mitbih/100.atr \
    demos/mitbih/out/story_record100.png demos/mitbih/out/story_record100.pdf
  git ls-files downloads/mitbih demos/mitbih/out
  "$PY" - <<'PY'
from pathlib import Path
png = Path("demos/mitbih/out/story_record100.png")
pdf = Path("demos/mitbih/out/story_record100.pdf")
print(f"png bytes {png.stat().st_size}")
print(f"pdf bytes {pdf.stat().st_size}")
print(pdf.read_bytes()[:8])
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

# Cache record 100 before ffmpeg starts, so the Run scene is the script
# and not a download stall. The story still calls load_record100.
"$PY" -m openmatlab.libs.mitbih fetch >/dev/null

xdotool search --name 'Google Chrome' windowminimize %@ 2>/dev/null || true
pkill -f 'xfce4-terminal' 2>/dev/null || true
pkill -f 'm15_driver.py' 2>/dev/null || true
sleep 0.5

if [[ "$MODE" != "--dry-run" ]]; then
  ffmpeg -y -video_size 1920x1200 -framerate 15 -f x11grab -draw_mouse 1 -i "$DISPLAY" \
    -c:v libx264 -pix_fmt yuv420p -preset veryfast -crf 23 \
    "$OUT" </dev/null 2>"$TMP/ffmpeg.log" &
  FFPID=$!
  sleep 0.5
fi

"$PY" demos/workbench/m15_driver.py "$ROOT/demos/mitbih" | tee "$TMP/timeline.txt"

if [[ "$MODE" != "--dry-run" ]]; then
  sleep 1
  kill -INT "$FFPID"; wait "$FFPID" 2>/dev/null || true; FFPID=""
  ls -la "$OUT"
  ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$OUT"
  # M13 copies next to the repo when the checkout is not /workspace itself.
  REC="/workspace/recordings"
  case "$REC" in
    "$ROOT"|"$ROOT"/*)
      echo "skip in-repo copy of $REC (checkout is $ROOT)"
      ;;
    *)
      mkdir -p "$REC"
      cp -f "$OUT" "$REC/showcase_m15_mitbih.mp4"
      echo "copied → $REC/showcase_m15_mitbih.mp4"
      ;;
  esac
fi
echo "--- timeline ---"
cat "$TMP/timeline.txt"
