"""Scripted GUI driver for the M14 C-MAPSS FD001 story (Epic #999, V08).

Launches the real tk Workbench (``Workbench.run_tk``) with cwd ``demos/cmapss``
and drives it with X pointer events (xdotool), the same way
``m13_driver.py`` records the graphics showcase. Scenes:

1. Current Folder opens ``story_fd001.m`` in the Editor.
2. Command Window sets ``DefaultFigureWindowStyle`` to ``docked`` so the
   Figures panel can show the charts.
3. Run. The Command Window prints the FD001 size, the V03–V07 lines, and
   the 300 dpi PNG/PDF paths.
4. Figures panel: the lab-meeting figure, then the raw / ``smoothdata`` axes.

The story directory is not rewritten. The Zenodo zip and the FD001 text stay
under ``downloads/cmapss/``. Used by ``record_m14_cmapss_showcase.sh``; not
part of the test suite.
"""

from __future__ import annotations

import subprocess
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import openmatlab.host.debug_ui as debug_ui
from openmatlab.host.workbench import Workbench

# One Run of the FD001 story is a batch, not a Step. The debugger wait is 60s,
# which is tight once export and a cold cache share that Run. This process only.
debug_ui._TIMEOUT = 180.0

ROOT = Path(__file__).resolve().parents[2]
DEMO = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else (ROOT / "demos" / "cmapss")
STORY = DEMO / "story_fd001.m"
if not STORY.is_file():
    raise SystemExit(f"m14 driver: story not found: {STORY}")

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


def click_widget(w, n=1):
    click_at(*center(w), n=n)


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
    if path is not None and path.name == "story_fd001.m":
        return
    print("WARN: list click missed; opening story_fd001.m through the folder binding", flush=True)
    cf_list = cf_listbox()
    if cf_list is None:
        return
    items = list(cf_list.get(0, "end"))
    i = next(k for k, s in enumerate(items) if s.endswith("story_fd001.m"))
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
    figs = state["wb"].figures.list()
    print(
        f"    -> figures {[(f.number, f.title, f.docked) for f in figs]} "
        f"focused={state['wb'].figures.focused()}",
        flush=True,
    )


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


def cw_eval_line(line: str) -> None:
    entry = find(
        lambda w: isinstance(w, ttk.Entry)
        and not isinstance(w, ttk.Combobox)
        and w.winfo_rooty() > 400
    )
    if entry is None:
        print("WARN: command entry missing", flush=True)
        state["wb"].command_window.eval(line)
        return
    # Click is queued before the keystrokes. Tk applies them in that order
    # once this function returns to the main loop (same as m13_driver).
    click_widget(entry)
    time.sleep(0.15)
    xdo("key", "ctrl+a")
    time.sleep(0.05)
    xdo("key", "BackSpace")
    subprocess.run(["xdotool", "type", "--delay", "18", "--", line], check=False)
    time.sleep(0.15)
    xdo("key", "Return")


def window_style() -> str:
    try:
        return str(state["wb"].command_window.eval("get(groot,'DefaultFigureWindowStyle')")).strip()
    except Exception as exc:
        print(f"WARN window style: {exc}", flush=True)
        return ""


def fig_listbox():
    focus_btn = button("Focus")
    if focus_btn is not None:
        frame = focus_btn.master.master
        for c in frame.winfo_children():
            if isinstance(c, tk.Listbox):
                return c
    for w in walk(state["root"]):
        try:
            if isinstance(w, tk.Listbox) and any("[docked]" in s for s in w.get(0, "end")):
                return w
        except tk.TclError:
            pass
    return None


def click_fig_refresh():
    b = button("Refresh")
    if b is None:
        return
    move_to(*center(b))
    time.sleep(0.2)
    b.invoke()
    state["root"].update_idletasks()
    lb = fig_listbox()
    items = list(lb.get(0, "end")) if lb is not None else []
    preview = []
    for w in walk(state["root"]):
        try:
            if isinstance(w, ttk.Notebook):
                labels = [w.tab(t, "text") for t in w.tabs()]
                if any(str(label).startswith("Fig ") for label in labels):
                    preview = labels
        except tk.TclError:
            pass
    print(f"    -> refresh {items} preview={preview}", flush=True)


def click_fig_entry(index: int) -> None:
    state["root"].update_idletasks()
    state["root"].lift()
    state["root"].focus_force()
    lb = fig_listbox()
    if lb is None or index < 0 or index >= lb.size():
        print(f"WARN: fig index {index} out of range", flush=True)
        return
    lb.see(index)
    lb.update_idletasks()
    bb = lb.bbox(index)
    if bb is None:
        n = max(lb.size(), 1)
        row_h = max(lb.winfo_height() // n, 18)
        x = lb.winfo_rootx() + 40
        y = lb.winfo_rooty() + index * row_h + row_h // 2
    else:
        x = lb.winfo_rootx() + bb[0] + 40
        y = lb.winfo_rooty() + bb[1] + bb[3] // 2
    click_at(x, y, n=1)
    time.sleep(0.15)
    lb.selection_clear(0, "end")
    lb.selection_set(index)
    lb.activate(index)
    handle = float(lb.get(index).split()[0])
    try:
        state["wb"].figures.focus(handle)
    except Exception as exc:
        print(f"WARN focus({handle}): {exc}", flush=True)
    lb.event_generate("<<ListboxSelect>>")
    state["root"].update_idletasks()
    b = button("Focus")
    if b is not None:
        move_to(*center(b))
        time.sleep(0.15)
        b.invoke()
        state["root"].update_idletasks()
    print(f"    -> focused={state['wb'].figures.focused()} list={list(lb.get(0, 'end'))}", flush=True)


def steps():
    root = state["root"]

    def s_intro():
        caption("M14 C-MAPSS FD001 — Workbench story (V01–V08). Data stays out of the repo.")
        root.after(6000, s_open)

    def s_open():
        caption("Open demos/cmapss/story_fd001.m — load, smooth, metrics, heatmap, export")
        open_from_cf("story_fd001.m")
        root.after(3500, s_opened)

    def s_opened():
        ensure_story()
        root.after(7000, s_dock)

    def s_dock():
        caption("Command Window: dock figures so the Figures panel can show them")
        cw_eval_line("set(groot,'DefaultFigureWindowStyle','docked');")
        root.after(3500, s_docked)

    def s_docked():
        style = window_style()
        print(f"    -> DefaultFigureWindowStyle={style!r}", flush=True)
        if "docked" not in style:
            state["wb"].command_window.eval("set(groot,'DefaultFigureWindowStyle','docked')")
            print("    -> set docked from the session", flush=True)
        root.after(4000, s_run)

    def s_run():
        caption("V08: Run story_fd001.m — Command Window fills when the script returns")
        run_script()
        dump_command_window()
        root.after(2500, s_head)

    def s_head():
        caption("V01/V02: FD001 train height, width, units, unit 1 cycles")
        see_command("1.0")
        root.after(10000, s_tail)

    def s_tail():
        caption("V03–V07: metrics, heatmap class, 300 dpi PNG and PDF")
        see_command("end")
        root.after(18000, s_refresh)

    def s_refresh():
        caption("V08: Figures panel — lab figure, then raw and smoothdata")
        click_fig_refresh()
        root.after(5000, s_lab)

    def s_lab():
        caption("V05/V06: lab figure — tiledlayout, heatmap, Saxena PHM08 footnote")
        click_fig_entry(0)
        root.after(22000, s_smooth)

    def s_smooth():
        caption("V03: last figure — raw, movmean, and gaussian on one axes")
        click_fig_entry(1)
        root.after(14000, s_done)

    def s_done():
        caption("M14 story done — export is demos/cmapss/out/ (gitignored). Zenodo CC BY 4.0.")
        root.after(12000, root.destroy)

    root.after(800, s_intro)


def _mainloop(self, n=0):
    root = state["root"]
    root.title("OpenMATLAB Workbench - M14 C-MAPSS FD001")
    root.geometry("1920x1140+0+0")
    cap = tk.Label(
        root,
        text="M14 C-MAPSS FD001 — waiting",
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
state["wb"].run_tk(title="OpenMATLAB Workbench - M14 C-MAPSS FD001")
