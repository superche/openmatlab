#!/usr/bin/env bash
# Record the M14 C-MAPSS FD001 story in the real tk Workbench (Epic #999 / V08–V09).
# Driver: demos/workbench/m14_driver.py
# Output: demos/workbench/showcase_m14_cmapss.mp4
#
# Shaw's box (same display as the M13 showcase):
#   DISPLAY=:2 ./demos/workbench/record_m14_cmapss_showcase.sh
# GUI without ffmpeg (M13 --dry-run):
#   DISPLAY=:2 ./demos/workbench/record_m14_cmapss_showcase.sh --dry-run
# No display: prove the story and the driver source, write no mp4:
#   ./demos/workbench/record_m14_cmapss_showcase.sh --headless
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source .venv/bin/activate
export DISPLAY="${DISPLAY:-:2}"
OUT="$ROOT/demos/workbench/showcase_m14_cmapss.mp4"
TMP="$(mktemp -d)"
FFPID=""
MODE="${1:-}"
trap 'kill -INT "$FFPID" 2>/dev/null || true; rm -rf "$TMP"' EXIT

headless_proof() {
  echo "M14 headless proof (no mp4; Workbench capture needs a display)"
  bash -n "$ROOT/demos/workbench/record_m14_cmapss_showcase.sh"
  bash -n "$ROOT/demos/cmapss/record_story_fd001.sh"
  python -c "import ast; from pathlib import Path; ast.parse(Path('demos/workbench/m14_driver.py').read_text())"
  echo "driver parses; record scripts pass bash -n"
  python -m openmatlab.libs.cmapss fetch
  openmatlab -e "run('demos/cmapss/story_fd001.m')"
  git check-ignore -v downloads/cmapss/CMAPSSData.zip downloads/cmapss/fd001/train_FD001.txt \
    demos/cmapss/out/story_fd001.png demos/cmapss/out/story_fd001.pdf
  git ls-files downloads/cmapss demos/cmapss/out
  python - <<'PY'
from pathlib import Path
png = Path("demos/cmapss/out/story_fd001.png")
pdf = Path("demos/cmapss/out/story_fd001.pdf")
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

# Cache the Zenodo zip before ffmpeg starts, so the Run scene is the script
# and not a download stall. The story still calls cmapss_fetch.
python -m openmatlab.libs.cmapss fetch >/dev/null

xdotool search --name 'Google Chrome' windowminimize %@ 2>/dev/null || true
pkill -f 'xfce4-terminal' 2>/dev/null || true
pkill -f 'm14_driver.py' 2>/dev/null || true
sleep 0.5

if [[ "$MODE" != "--dry-run" ]]; then
  ffmpeg -y -video_size 1920x1200 -framerate 15 -f x11grab -draw_mouse 1 -i "$DISPLAY" \
    -c:v libx264 -pix_fmt yuv420p -preset veryfast -crf 23 \
    "$OUT" </dev/null 2>"$TMP/ffmpeg.log" &
  FFPID=$!
  sleep 0.5
fi

python demos/workbench/m14_driver.py "$ROOT/demos/cmapss" | tee "$TMP/timeline.txt"

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
      cp -f "$OUT" "$REC/showcase_m14_cmapss.mp4"
      echo "copied → $REC/showcase_m14_cmapss.mp4"
      ;;
  esac
fi
echo "--- timeline ---"
cat "$TMP/timeline.txt"
