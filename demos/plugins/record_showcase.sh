#!/usr/bin/env bash
# Re-record plugin host showcase: community package call AND desktop panel.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source .venv/bin/activate
export DISPLAY="${DISPLAY:-:2}"
OUT="$ROOT/demos/plugins/showcase_plugin_host.mp4"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Hide Chrome / other non-showcase windows
wmctrl -r 'Google Chrome' -b add,hidden 2>/dev/null || true
xdotool search --name 'Google Chrome' windowminimize %@ 2>/dev/null || true
pkill -f 'xfce4-terminal' 2>/dev/null || true
pkill -f 'openmatlab desktop' 2>/dev/null || true
sleep 0.5

cat > "$TMP/demo.sh" <<'DEMO'
#!/usr/bin/env bash
set -e
cd /workspace/openmatlab
source .venv/bin/activate
clear
echo "# OpenMATLAB plugin host showcase — community package + desktop panel"
echo "# Epic #349 · Issues #367 #368"
sleep 1
echo
echo ">> openmatlab plugins --path demos/plugins/community.signal --no-user-dir --no-entry-points --activate"
openmatlab plugins --path demos/plugins/community.signal --no-user-dir --no-entry-points --activate
sleep 1
echo
echo ">> python: PluginHost execute_command + which(hamming)"
python - <<'PY'
from openmatlab.extensions import PluginHost
from openmatlab.libs.path import ToolboxPath
h = PluginHost(toolbox_path=ToolboxPath())
h.discover(extra=["demos/plugins/community.signal"], include_user_dir=False, include_entry_points=False)
h.load_all(); h.activate_on_startup()
print(h.execute_command("community.signal.demo"))
print("which", h.path_api.which("hamming"))
PY
sleep 2
echo
echo ">> openmatlab desktop --list-only"
openmatlab desktop --path demos/plugins/community.signal --list-only
sleep 1
echo
echo ">> openmatlab desktop --demo-ms 8000   # panel UI"
openmatlab desktop --path demos/plugins/community.signal --demo-ms 8000
echo
echo "# done — package call + desktop panel shown"
sleep 3
DEMO
chmod +x "$TMP/demo.sh"

xfce4-terminal \
  --fullscreen \
  --title="OpenMATLAB showcase" \
  --hide-menubar \
  --hide-toolbar \
  --hide-scrollbar \
  -e "bash $TMP/demo.sh" &
TERM_PID=$!
sleep 1.2

ffmpeg -y -video_size 1920x1200 -framerate 15 -f x11grab -i "$DISPLAY" \
  -t 30 -c:v libx264 -pix_fmt yuv420p -preset ultrafast -crf 28 \
  "$OUT" </dev/null 2>"$TMP/ffmpeg.log"

wait "$TERM_PID" 2>/dev/null || true
pkill -f 'xfce4-terminal' 2>/dev/null || true
ls -la "$OUT"
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$OUT" || true
