"""Scripted GUI driver for the M17 analyst story (issue #1034).

Launches the real tk Workbench (``Workbench.run_tk``) with cwd ``demos/analyst``
and drives it with X pointer events (xdotool), the same way
``m16_driver.py`` records the BBBC038 showcase. Scenes:

1. Current Folder opens ``story_assays.m`` in the Editor.
2. Run. The Command Window prints the missing-value counts, the four
   group lines (West count 0, means NaN), and the CSV paths.
3. The window holds on the head of that transcript, then on the tail.

The story directory is not rewritten. Generated CSV stays under
``demos/analyst/out/`` and is gitignored. Used by
``record_m17_analyst_showcase.sh``; not part of the test suite.
"""

from __future__ import annotations

import subprocess
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from openmatlab.host.workbench import Workbench

ROOT = Path(__file__).resolve().parents[2]
DEMO = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else (ROOT / "demos" / "analyst")
STORY = DEMO / "story_assays.m"
if not STORY.is_file():
    raise SystemExit(f"m17 driver: story not found: {STORY}")

state: dict = {}
_orig_init = tk.Tk.__init__
_orig_mainloop = tk.Misc.mainloop


def _init(self, *a, **k):
    _orig_init(self, *a, **k)
    self.tk.call("tk", "scaling", 1.6)
    for name in ("TkDefaultFont", "TkTextFont", "TkHeadingFont", "TkMenuFont", "TkFixedFont"):
        try:
            self.tk.call("font", "configure", name, "-size", 11)
        except tk.TclError:
            pass
    state["root"] = self
    st = ttk.Style(self)
    st.configure("Treeview", rowheight=28)
    st.configure("Treeview.Heading", font=("DejaVu Sans", 11, "bold"))


def walk(w):
    yield w
    for c in w.winfo_children():
        yield from walk(c)


def find(pred):
    for w in walk(state["root"]):
        try:
            if pred(w):
                return w
        except tk.TclError:
            pass
    return None


def button(text):
    return find(lambda w: isinstance(w, ttk.Button) and w.cget("text") == text)


def xdo(*args):
    subprocess.run(["xdotool", *map(str, args)], check=False)


def move_to(x, y):
    xdo("mousemove", "--sync", int(x), int(y))


def click_at(x, y, n=1):
    move_to(x, y)
    time.sleep(0.25)
    xdo("click", "--repeat", n, "--delay", 120, 1)


def center(w):
    w.update_idletasks()
    return w.winfo_rootx() + w.winfo_width() // 2, w.winfo_rooty() + w.winfo_height() // 2


def caption(text):
    state["cap"].configure(text=text)
    print(f"[{time.monotonic() - state['t0']:6.1f}s] {text}", flush=True)


def cf_listbox():
    return find(lambda w: isinstance(w, tk.Listbox) and w.winfo_height() > 200)


def open_from_cf(filename: str):
    cf_list = cf_listbox()
    if cf_list is None:
        print("WARN: current-folder list missing", flush=True)
        return
    items = list(cf_list.get(0, "end"))
    i = next(k for k, s in enumerate(items) if s.endswith(filename))
    cf_list.see(i)
    cf_list.update_idletasks()
    bb = cf_list.bbox(i)
    if bb is None:
        print(f"WARN: no bbox for {filename}", flush=True)
        return
    click_at(cf_list.winfo_rootx() + bb[0] + 60, cf_list.winfo_rooty() + bb[1] + bb[3] // 2, n=2)


def ensure_story():
    path = state["wb"].editor.path
    print(f"    -> editor {path}", flush=True)
    if path is not None and path.name == "story_assays.m":
        return
    print("WARN: list click missed; opening story_assays.m through the folder binding", flush=True)
    cf_list = cf_listbox()
    if cf_list is None:
        return
    items = list(cf_list.get(0, "end"))
    i = next(k for k, s in enumerate(items) if s.endswith("story_assays.m"))
    cf_list.selection_clear(0, "end")
    cf_list.selection_set(i)
    cf_list.activate(i)
    cf_list.event_generate("<Double-Button-1>")


def run_script():
    """Pointer on Run, then invoke() so the story finishes before the next scene."""
    b = button("Run")
    if b is None:
        print("WARN: Run button missing", flush=True)
        return
    move_to(*center(b))
    time.sleep(0.3)
    t = time.monotonic()
    b.invoke()
    state["root"].update_idletasks()
    print(f"    -> Run returned in {time.monotonic() - t:.1f}s", flush=True)


def command_text():
    texts = []
    for w in walk(state["root"]):
        try:
            if isinstance(w, tk.Text):
                texts.append(w)
        except tk.TclError:
            pass
    if not texts:
        return None
    texts.sort(key=lambda w: w.winfo_rooty())
    return texts[-1]


def dump_command_window():
    w = command_text()
    if w is None:
        print("WARN: command window text missing", flush=True)
        return
    w.see("end")
    body = w.get("1.0", "end").rstrip()
    print("--- command window ---", flush=True)
    print(body, flush=True)
    print("--- end command window ---", flush=True)


def see_command(index: str):
    w = command_text()
    if w is not None:
        w.see(index)
        w.update_idletasks()


def steps():
    root = state["root"]

    def s_intro():
        caption("M17 analyst story — wash a field log, then groupsummary, then writetable.")
        root.after(5000, s_open)

    def s_open():
        caption("Open demos/analyst/story_assays.m — TreatAsMissing, fill, empty West group")
        open_from_cf("story_assays.m")
        root.after(3500, s_opened)

    def s_opened():
        ensure_story()
        root.after(7000, s_run)

    def s_run():
        caption("Run story_assays.m — Command Window fills when the script returns")
        run_script()
        dump_command_window()
        root.after(2000, s_head)

    def s_head():
        caption("Missing counts: site 2, moisture 3, temp 2, qc 2, total 9")
        see_command("1.0")
        root.after(12000, s_tail)

    def s_tail():
        caption("West count 0, means NaN. CSV is demos/analyst/out/ (gitignored).")
        see_command("end")
        root.after(16000, s_done)

    def s_done():
        caption("M17 story done — site_summary.csv and cleaned.csv stay out of the repo.")
        root.after(8000, root.destroy)

    root.after(800, s_intro)


def _mainloop(self, n=0):
    root = state["root"]
    root.title("OpenMATLAB Workbench - M17 Analyst")
    root.geometry("1920x1140+0+0")
    cap = tk.Label(
        root,
        text="M17 analyst story — waiting",
        font=("DejaVu Sans", 15, "bold"),
        bg="#1f3a5f",
        fg="white",
        anchor="w",
        padx=12,
        pady=6,
    )
    cap.pack(side="bottom", fill="x", before=root.pack_slaves()[0])
    state["cap"] = cap
    state["t0"] = time.monotonic()
    root.after(400, lambda: (root.lift(), root.focus_force(), root.attributes("-topmost", True)))
    root.after(900, lambda: root.attributes("-topmost", False))
    root.after(300, steps)
    _orig_mainloop(self, n)


def _fontfix(cls):
    orig = cls.__init__

    def init(self, *a, **k):
        f = k.get("font")
        if isinstance(f, tuple) and f and f[0] == "Courier":
            k["font"] = ("DejaVu Sans Mono", 11)
        elif isinstance(f, tuple) and f and f[0] == "":
            k["font"] = ("DejaVu Sans",) + tuple(f[1:])
        if cls is tk.Listbox and int(k.get("height", 4)) > 12:
            k["height"] = 12
        if cls is ttk.Treeview:
            k["height"] = min(int(k.get("height", 5)), 6)
        orig(self, *a, **k)

    cls.__init__ = init


for _cls in (tk.Text, tk.Listbox, ttk.Entry, ttk.Label, ttk.Treeview):
    _fontfix(_cls)

tk.Tk.__init__ = _init
tk.Misc.mainloop = _mainloop

state["wb"] = Workbench.create(cwd=DEMO)
state["wb"].run_tk(title="OpenMATLAB Workbench - M17 Analyst")
