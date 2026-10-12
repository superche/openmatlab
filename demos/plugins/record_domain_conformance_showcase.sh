#!/usr/bin/env bash
# Record Epic #371 domain business-conformance showcase:
# LARGE font, clear fullscreen terminal only — hamming(8) vs golden + PluginHost which.
# Keep under 90s. Output: demos/plugins/showcase_domain_conformance.mp4
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source .venv/bin/activate
export DISPLAY="${DISPLAY:-:2}"
OUT="$ROOT/demos/plugins/showcase_domain_conformance.mp4"
TMP="$(mktemp -d)"
TERM_DONE="$TMP/term_done"
trap 'rm -rf "$TMP"; pkill -f "xfce4-terminal.*OpenMATLAB domain" 2>/dev/null || true; kill "$FFPID" 2>/dev/null || true' EXIT

# Hide Chrome / other non-showcase windows — clear window
wmctrl -r 'Google Chrome' -b add,hidden 2>/dev/null || true
xdotool search --name 'Google Chrome' windowminimize %@ 2>/dev/null || true
pkill -f 'xfce4-terminal' 2>/dev/null || true
pkill -f 'openmatlab desktop' 2>/dev/null || true
sleep 0.5

cat > "$TMP/term.sh" <<DEMO
#!/usr/bin/env bash
set -e
cd /workspace/openmatlab
source .venv/bin/activate
clear
echo "############################################################"
echo "# OpenMATLAB domain business-conformance showcase"
echo "# Epic #371 · D01 hamming(8) vs golden · D04 PluginHost which"
echo "############################################################"
sleep 1.5

echo
echo '=== 1 reference-vector tests (pytest conformance) ==='
echo ">> pytest tests/conformance -m conformance -q"
pytest tests/conformance -m conformance -q --tb=no
sleep 2.0

echo
echo '=== 2 hamming(8) vs golden (D01) ==='
echo ">> python: Session + community.signal hamming(8) compare golden"
python - <<'PY'
from pathlib import Path
import json
import numpy as np
from openmatlab.host.display import NullDisplay
from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

PLUGIN_MFILES = Path("demos/plugins/community.signal/mfiles")
SCRIPTS = Path("tests/conformance/scripts")
expected = json.loads((SCRIPTS / "d01_hamming.expected.json").read_text())
golden = np.asarray(expected["h8"], dtype=float).ravel()

s = Session.create_default()
s.display = NullDisplay()
r = ReplSession(s)
r.run_line(f'addpath("{PLUGIN_MFILES.as_posix()}");')
r.run_line("h8 = hamming(8);")
got = np.asarray(s.workspace.get("h8").backend_buffer(), dtype=float).ravel()

def fmt(a):
    return "[" + " ".join(f"{v:.6g}" for v in a) + "]"

print("hamming(8) =", fmt(got))
print("golden     =", fmt(golden))
print("match      =", bool(np.allclose(got, golden)))
assert np.allclose(got, golden), "hamming(8) must match golden reference vector"
print("D01 hamming(8) vs golden: PASS")
PY
sleep 3.0

echo
echo '=== 3 PluginHost which gate (D04) ==='
echo ">> python: PluginHost discover → activate → which('hamming')"
python - <<'PY'
from pathlib import Path
from openmatlab.extensions import PluginHost
from openmatlab.libs.path import ToolboxPath

PLUGIN_ROOT = Path("demos/plugins/community.signal")
h = PluginHost(toolbox_path=ToolboxPath())
h.bind_apis()
warns = h.discover(
    extra=[PLUGIN_ROOT],
    include_user_dir=False,
    include_entry_points=False,
)
h.load_all()
h.activate_on_startup()
hit = h.path_api.which("hamming")
print("which(hamming) ->", hit)
assert hit is not None
assert Path(hit).name == "hamming.m"
assert "community.signal" in Path(hit).as_posix()
print("D04 PluginHost which gate: PASS")
PY
sleep 3.0

echo
echo "############################################################"
echo "# Epic #371 domain conformance showcase — DONE"
echo "# D01 hamming(8) vs golden PASS · D04 which PASS"
echo "############################################################"
sleep 2.5
touch "$TERM_DONE"
sleep 4.0
DEMO
chmod +x "$TMP/term.sh"

# Start capture first so terminal open is on video
FFPID=""
ffmpeg -y -video_size 1920x1200 -framerate 12 -f x11grab -i "$DISPLAY" \
  -c:v libx264 -pix_fmt yuv420p -preset ultrafast -crf 26 \
  "$OUT" </dev/null 2>"$TMP/ffmpeg.log" &
FFPID=$!
sleep 0.5

xfce4-terminal \
  --disable-server \
  --fullscreen \
  --title="OpenMATLAB domain conformance" \
  --hide-menubar \
  --hide-toolbar \
  --hide-scrollbar \
  --font='DejaVu Sans Mono 22' \
  -e "bash $TMP/term.sh" &
TERM_PID=$!

for _ in $(seq 1 200); do
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
# Hold on DONE banner a bit longer, stop ffmpeg WHILE terminal still visible
sleep 3.5
kill -INT "$FFPID" 2>/dev/null || true
wait "$FFPID" 2>/dev/null || true
FFPID=""
sleep 0.2
pkill -f 'xfce4-terminal' 2>/dev/null || true
wait "$TERM_PID" 2>/dev/null || true

ls -la "$OUT"
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$OUT" || true
