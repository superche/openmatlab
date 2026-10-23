#!/usr/bin/env bash
# Record the M12 corpus-gate showcase (Epic #765 / C07+C08):
# clean fullscreen xfce4-terminal showing REPORT rates, 1–2 T3 golden scripts, pytest 11 passed.
# Output: demos/corpus/showcase_m12_corpus.mp4 (copy also to /workspace/recordings/)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source .venv/bin/activate
export DISPLAY="${DISPLAY:-:2}"
OUT="$ROOT/demos/corpus/showcase_m12_corpus.mp4"
TMP="$(mktemp -d)"
TERM_DONE="$TMP/term_done"
FFPID=""
DRY="${1:-}"
trap 'rm -rf "$TMP"; pkill -f "xfce4-terminal.*M12 corpus" 2>/dev/null || true; kill -INT "$FFPID" 2>/dev/null || true' EXIT

xdotool search --name 'Google Chrome' windowminimize %@ 2>/dev/null || true
pkill -f 'xfce4-terminal' 2>/dev/null || true
sleep 0.5

cat > "$TMP/term.sh" <<DEMO
#!/usr/bin/env bash
set -e
cd /workspace/openmatlab
source .venv/bin/activate
export TERM=xterm-256color
clear
echo "############################################################"
echo "# OpenMATLAB M12 Corpus Gate showcase"
echo "# Epic #765 · C07 T2 + C08 T3 (M12 10/10 criteria met)"
echo "############################################################"
sleep 3.5

echo
echo "=== 1 docs/corpus/REPORT.md — pass rates by tier ==="
echo ">> sed -n '1,25p' docs/corpus/REPORT.md"
sleep 1.0
sed -n '1,25p' docs/corpus/REPORT.md
echo
echo "(C08 T3 golden = 75.3 % >= 70 % locked threshold; C07 T2 = 82.8 % >= 75 %)"
sleep 14.0

echo
echo "=== 2 T3 golden sample source (deprompted; corpus cache never committed) ==="
echo ">> cat demos/corpus/samples/t3_Boolean_values_1.m"
sleep 0.8
cat demos/corpus/samples/t3_Boolean_values_1.m
sleep 7.0

echo
echo "=== 3 Run T3 golden: rosetta/Boolean_values/1 ==="
echo ">> openmatlab run demos/corpus/samples/t3_Boolean_values_1.m"
sleep 0.8
openmatlab run demos/corpus/samples/t3_Boolean_values_1.m
sleep 8.0

echo
echo "=== 4 Run T3 golden: rosetta/Sum_and_product_of_an_array/1 ==="
echo ">> openmatlab run demos/corpus/samples/t3_Sum_and_product_of_an_array_1.m"
sleep 0.8
openmatlab run demos/corpus/samples/t3_Sum_and_product_of_an_array_1.m
sleep 8.0

echo
echo "=== 5 M12 conformance gate (11 criteria) ==="
echo ">> pytest tests/conformance/test_m12_conformance.py --tb=no -q"
sleep 0.8
pytest tests/conformance/test_m12_conformance.py --tb=no -q
sleep 9.0

echo
echo "############################################################"
echo "# M12 showcase DONE"
echo "# T0 99.5% | T1 70.5% | T2 82.8% (C07) | T3 75.3% (C08)"
echo "# Conformance: 11/11 passed — milestone 10/10 met"
echo "# Epics #765-#766 stay OPEN pending Shaw acceptance"
echo "############################################################"
sleep 8.0
touch "$TERM_DONE"
sleep 2.5
DEMO
chmod +x "$TMP/term.sh"

if [[ "$DRY" == "--dry-run" ]]; then
  bash "$TMP/term.sh"
  exit 0
fi

ffmpeg -y -video_size 1920x1200 -framerate 12 -f x11grab -i "$DISPLAY" \
  -c:v libx264 -pix_fmt yuv420p -preset ultrafast -crf 26 \
  "$OUT" </dev/null 2>"$TMP/ffmpeg.log" &
FFPID=$!
sleep 0.5

xfce4-terminal \
  --disable-server \
  --fullscreen \
  --title="OpenMATLAB M12 corpus showcase" \
  --hide-menubar \
  --hide-toolbar \
  --hide-scrollbar \
  --font='DejaVu Sans Mono 18' \
  -e "bash $TMP/term.sh" &
TERM_PID=$!

for _ in $(seq 1 600); do
  if [[ -f "$TERM_DONE" ]]; then
    break
  fi
  sleep 0.25
done
if [[ ! -f "$TERM_DONE" ]]; then
  echo "ERROR: terminal phase did not signal done" >&2
  kill -INT "$FFPID" 2>/dev/null || true
  exit 1
fi
sleep 2.0
kill -INT "$FFPID" 2>/dev/null || true
wait "$FFPID" 2>/dev/null || true
FFPID=""
sleep 0.2
pkill -f 'xfce4-terminal' 2>/dev/null || true
wait "$TERM_PID" 2>/dev/null || true

ls -la "$OUT"
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$OUT" || true
mkdir -p /workspace/recordings
cp -f "$OUT" /workspace/recordings/showcase_m12_corpus.mp4
echo "copied → /workspace/recordings/showcase_m12_corpus.mp4"
