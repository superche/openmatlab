#!/usr/bin/env bash
# Record the M16 BBBC038 stage1_test story in the real tk Workbench (Epic #1025 / V08–V09).
# Driver: demos/workbench/m16_driver.py
# Output: demos/workbench/showcase_m16_bbbc038.mp4
#
# Shaw's box (same display as the M15 showcase):
#   DISPLAY=:2 ./demos/workbench/record_m16_bbbc038_showcase.sh
# GUI without ffmpeg:
#   DISPLAY=:2 ./demos/workbench/record_m16_bbbc038_showcase.sh --dry-run
# No display: prove the story and the driver source, write no mp4:
#   ./demos/workbench/record_m16_bbbc038_showcase.sh --headless
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
OUT="$ROOT/demos/workbench/showcase_m16_bbbc038.mp4"
TMP="$(mktemp -d)"
FFPID=""
MODE="${1:-}"
trap 'kill -INT "$FFPID" 2>/dev/null || true; rm -rf "$TMP"' EXIT

headless_proof() {
  echo "M16 headless proof (no mp4; Workbench capture needs a display)"
  bash -n "$ROOT/demos/workbench/record_m16_bbbc038_showcase.sh"
  bash -n "$ROOT/demos/bbbc038/record_story_stage1_test.sh"
  "$PY" -c "import ast; from pathlib import Path; ast.parse(Path('demos/workbench/m16_driver.py').read_text())"
  echo "driver parses; record scripts pass bash -n"
  openmatlab -e "run('demos/bbbc038/story_stage1_test.m')"
  git check-ignore -v downloads/bbbc038/stage1_test.zip \
    downloads/bbbc038/fov/0114f484a16c152baa2d82fdd43740880a762c93f436c8988ac461c5c9dbe7d5.png \
    demos/bbbc038/out/story_stage1_test.png demos/bbbc038/out/story_stage1_test.pdf
  git ls-files downloads/bbbc038 demos/bbbc038/out
  "$PY" - <<'PY'
from pathlib import Path
png = Path("demos/bbbc038/out/story_stage1_test.png")
pdf = Path("demos/bbbc038/out/story_stage1_test.pdf")
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

# Cache the zip before ffmpeg starts, so the Run scene is the script
# and not a download stall. The story still calls load_fov.
if [[ ! -f "$ROOT/downloads/bbbc038/stage1_test.zip" ]]; then
  openmatlab -e "bbbc038_fetch();"
fi

xdotool search --name 'Google Chrome' windowminimize %@ 2>/dev/null || true
pkill -f 'xfce4-terminal' 2>/dev/null || true
pkill -f 'm16_driver.py' 2>/dev/null || true
sleep 0.5

if [[ "$MODE" != "--dry-run" ]]; then
  ffmpeg -y -video_size 1920x1200 -framerate 15 -f x11grab -draw_mouse 1 -i "$DISPLAY" \
    -c:v libx264 -pix_fmt yuv420p -preset veryfast -crf 23 \
    "$OUT" </dev/null 2>"$TMP/ffmpeg.log" &
  FFPID=$!
  sleep 0.5
fi

"$PY" demos/workbench/m16_driver.py "$ROOT/demos/bbbc038" | tee "$TMP/timeline.txt"

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
      cp -f "$OUT" "$REC/showcase_m16_bbbc038.mp4"
      echo "copied → $REC/showcase_m16_bbbc038.mp4"
      ;;
  esac
fi
echo "--- timeline ---"
cat "$TMP/timeline.txt"
