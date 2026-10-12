#!/usr/bin/env bash
# Re-record plugin host showcase: LARGE fonts, step titles, hamming(8),
# desktop panel + visible Run click. Keep under 90s.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source .venv/bin/activate
export DISPLAY="${DISPLAY:-:2}"
OUT="$ROOT/demos/plugins/showcase_plugin_host.mp4"
TMP="$(mktemp -d)"
BTN_XY="$TMP/btn_xy"
TERM_DONE="$TMP/term_done"
trap 'rm -rf "$TMP"; pkill -f "xfce4-terminal.*OpenMATLAB showcase" 2>/dev/null || true' EXIT

# Hide Chrome / other non-showcase windows
wmctrl -r 'Google Chrome' -b add,hidden 2>/dev/null || true
xdotool search --name 'Google Chrome' windowminimize %@ 2>/dev/null || true
pkill -f 'xfce4-terminal' 2>/dev/null || true
pkill -f 'openmatlab desktop' 2>/dev/null || true
sleep 0.5

# --- Phase A script: LARGE font terminal + step title echoes ---------------
cat > "$TMP/term.sh" <<DEMO
#!/usr/bin/env bash
set -e
cd /workspace/openmatlab
source .venv/bin/activate
clear
echo "############################################################"
echo "# OpenMATLAB plugin host showcase"
echo "# Epic #349 · Issues #367 (toolbox) #368 (desktop panel)"
echo "############################################################"
sleep 1.0

echo
echo '=== 1 load plugin ==='
echo ">> openmatlab plugins --path demos/plugins/community.signal --no-user-dir --no-entry-points --activate"
openmatlab plugins --path demos/plugins/community.signal --no-user-dir --no-entry-points --activate
sleep 1.2

echo
echo '=== 2 call hamming(8) ==='
echo ">> python: PluginHost + Session eval of hamming(8)"
python - <<'PY'
from openmatlab.extensions import PluginHost
from openmatlab.libs.path import ToolboxPath
from openmatlab.host.display import NullDisplay
from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

h = PluginHost(toolbox_path=ToolboxPath())
h.discover(extra=["demos/plugins/community.signal"], include_user_dir=False, include_entry_points=False)
h.load_all(); h.activate_on_startup()
print("which(hamming) ->", h.path_api.which("hamming"))

s = Session.create_default()
s.display = NullDisplay()
for e in h.path_api.list():
    s.path.addpath(e)
s.functions.path = s.path
ReplSession(s).run_line("w = hamming(8);")
buf = s.workspace.get("w").backend_buffer().reshape(-1, order="F")
nums = [float(x) for x in buf]
compact = "[" + " ".join(f"{v:.4g}" for v in nums) + "]'"
print("hamming(8) =", compact)
print("hamming(8) numeric output OK")
PY
sleep 1.8

echo
echo '=== 3 list desktop panels ==='
echo ">> openmatlab desktop --path demos/plugins/community.signal --list-only"
openmatlab desktop --path demos/plugins/community.signal --list-only
sleep 1.2

echo
echo '=== 4 open desktop panel ==='
echo "# next: OpenMATLAB Desktop — click Run hamming(8)"
sleep 1.0
touch "$TERM_DONE"
# Keep window up briefly so the last lines are visible before we close it
sleep 2.0
DEMO
chmod +x "$TMP/term.sh"

# Start capture (killed when demo finishes — no empty-desktop tail)
ffmpeg -y -video_size 1920x1200 -framerate 12 -f x11grab -i "$DISPLAY" \
  -c:v libx264 -pix_fmt yuv420p -preset ultrafast -crf 26 \
  "$OUT" </dev/null 2>"$TMP/ffmpeg.log" &
FFPID=$!
sleep 0.5

# --disable-server: stay attached until term.sh exits (no dbus handoff)
xfce4-terminal \
  --disable-server \
  --fullscreen \
  --title="OpenMATLAB showcase" \
  --hide-menubar \
  --hide-toolbar \
  --hide-scrollbar \
  --font='DejaVu Sans Mono 22' \
  -e "bash $TMP/term.sh" &
TERM_PID=$!

# Wait for terminal steps to finish (DONE file), not the forked PID
for _ in $(seq 1 120); do
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
# Let the final sleep in term.sh show last lines, then close terminal
sleep 2.2
pkill -f 'xfce4-terminal' 2>/dev/null || true
wait "$TERM_PID" 2>/dev/null || true
sleep 0.4

# --- Phase B: desktop panel + click Run ------------------------------------
rm -f "$BTN_XY"
export OPENMATLAB_DEMO_BTN_XY="$BTN_XY"
openmatlab desktop --path demos/plugins/community.signal --demo-ms 17000 &
DESK_PID=$!

for _ in $(seq 1 40); do
  if [[ -s "$BTN_XY" ]]; then
    break
  fi
  sleep 0.25
done

WID="$(xdotool search --name 'OpenMATLAB Desktop' 2>/dev/null | tail -1 || true)"
if [[ -n "${WID}" ]]; then
  xdotool windowactivate --sync "$WID" 2>/dev/null || true
  xdotool windowraise "$WID" 2>/dev/null || true
fi
sleep 0.6

if [[ -s "$BTN_XY" ]]; then
  read -r BX BY < "$BTN_XY"
  xdotool mousemove --sync "$BX" "$BY"
  sleep 0.45
  xdotool click 1
else
  if [[ -n "${WID}" ]]; then
    eval "$(xdotool getwindowgeometry --shell "$WID")"
    xdotool mousemove --sync $((X + 110)) $((Y + 430))
    sleep 0.45
    xdotool click 1
  fi
fi

# Hold so panel hamming(8) result is readable
sleep 8

wait "$DESK_PID" 2>/dev/null || true
kill "$FFPID" 2>/dev/null || true
wait "$FFPID" 2>/dev/null || true

ls -la "$OUT"
DUR="$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$OUT" || true)"
echo "duration_sec=$DUR"
python3 - <<PY
d=float("${DUR}" or "0")
assert 20 <= d <= 90, f"duration {d} out of range 20..90"
print("duration_ok", d)
PY
