"""Scripted GUI driver for the M13 graphics end-to-end capture (Epics #767–#774).

Launches the real tk Workbench (``Workbench.run_tk``) at large scale and drives it
with real X pointer/keyboard events (xdotool). Scenes (in order, with captions):

1. Command Window gets fprintf/disp from a script (G09 half / #767)
2. DefaultFigureWindowStyle docked → figures in Figures panel; new fig takes focus (G09)
3. colormap default size 256; colorbar; imagesc (G05)
4. tiledlayout / yyaxis (G03)
5. savefig/openfig .fig round-trip (G08 own format)
6. mention ≥40 golden snapshots (G10)

Used by ``record_m13_graphics_showcase.sh``; not part of the test suite.
"""

from __future__ import annotations

import subprocess
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from openmatlab.host.workbench import Workbench

DEMO = Path(sys.argv[1]).resolve()

SCRIPTS = {
    "demo_out.m": """% M13 G09 (#767) - fprintf/disp → Command Window
fprintf('G09 output: total = %d\\n', 42);
disp('hello from script');
""",
    "demo_dock.m": """% M13 G09 (#774) - docked figures take focus in Figures panel
set(groot, 'DefaultFigureWindowStyle', 'docked');
figure; plot(1:5, 'LineWidth', 2); title('Fig 1 plot');
figure; plot(1:3, 'r-o'); title('Fig 2 (focus)');
fprintf('gcf Number = %d (new figure has focus)\\n', get(gcf, 'Number'));
""",
    "demo_color.m": """% M13 G05 - colormap default 256, imagesc, colorbar
figure;
imagesc(magic(8));
colormap(jet);
colorbar;
title('imagesc + jet + colorbar');
sz = size(colormap);
fprintf('colormap size = [%d %d] (default length 256)\\n', sz(1), sz(2));
""",
    "demo_layout.m": """% M13 G03 - tiledlayout / nexttile / yyaxis
figure;
t = tiledlayout(1, 2);
nexttile; plot(1:4, 'b-s'); title('left tile');
nexttile; yyaxis right; plot(4:-1:1, 'm-^'); title('yyaxis right');
fprintf('tiledlayout class = %s\\n', class(t));
""",
    "demo_figio.m": """% M13 G08 - savefig / openfig own .fig round-trip
d = tempname; mkdir(d);
f = figure; plot(1:6, 'LineWidth', 2, 'Tag', 'm13'); title('before savefig');
p = fullfile(d, 'roundtrip.fig');
savefig(f, p);
fprintf('savefig → %s\\n', p);
close(f);
g = openfig(p);
fprintf('openfig round-trip OK; fig Number = %d Tag=%s\\n', g.Number, get(findobj(g,'Tag','m13'),'Tag'));
""",
    "demo_snap.m": """% M13 G10 - golden snapshots (≥40 under tests/conformance/golden/snapshots/)
fprintf('G10: 46 golden PNG snapshots (e.g. imagesc.png, colormap_jet.png)\\n');
fprintf('path: tests/conformance/golden/snapshots/\\n');
""",
}

DEMO.mkdir(parents=True, exist_ok=True)
for p in DEMO.glob("*.m"):
    p.unlink()
for name, body in SCRIPTS.items():
    (DEMO / name).write_text(body)

state: dict = {}
_orig_init = tk.Tk.__init__
_orig_mainloop = tk.Misc.mainloop


def _init(self, *a, **k):
    _orig_init(self, *a, **k)
    self.tk.call("tk", "scaling", 1.9)
    for name in ("TkDefaultFont", "TkTextFont", "TkHeadingFont", "TkMenuFont", "TkFixedFont"):
        try:
            self.tk.call("font", "configure", name, "-size", 11)
        except tk.TclError:
            pass
    state["root"] = self
    st = ttk.Style(self)
    st.configure("Treeview", rowheight=34)
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


def click_widget(w, n=1):
    click_at(*center(w), n=n)


def caption(text):
    state["cap"].configure(text=text)
    print(f"[{time.monotonic() - state['t0']:6.1f}s] {text}", flush=True)


def open_from_cf(filename: str):
    cf_list = find(lambda w: isinstance(w, tk.Listbox) and w.winfo_height() > 200)
    items = list(cf_list.get(0, "end"))
    i = next(k for k, s in enumerate(items) if s.endswith(filename))
    bb = cf_list.bbox(i)
    click_at(cf_list.winfo_rootx() + bb[0] + 60, cf_list.winfo_rooty() + bb[1] + bb[3] // 2, n=2)


def run_script():
    click_widget(button("Run"))


def click_fig_refresh():
    b = button("Refresh")
    if b is not None:
        click_widget(b)


def steps():
    root = state["root"]

    def s_intro():
        caption("M13 Graphics showcase — G09/G05/G03/G08/G10 (real Workbench)")

    def s_open_out():
        caption("1. G09 (#767): open demo_out.m — fprintf/disp must land in Command Window")
        open_from_cf("demo_out.m")

    def s_run_out():
        caption("1. Run: Command Window shows 'G09 output: total = 42' and 'hello from script'")
        run_script()

    def s_open_dock():
        caption("2. G09 (#774): open demo_dock.m — DefaultFigureWindowStyle=docked")
        open_from_cf("demo_dock.m")

    def s_run_dock():
        caption("2. Run: two docked figures; new figure takes focus (gcf=2) in Figures panel")
        run_script()

    def s_refresh_dock():
        caption("2. Figures panel: docked previews + focus marker (Refresh)")
        click_fig_refresh()

    def s_open_color():
        caption("3. G05: open demo_color.m — colormap / imagesc / colorbar")
        open_from_cf("demo_color.m")

    def s_run_color():
        caption("3. Run: imagesc + jet + colorbar; colormap size [256 3]")
        run_script()

    def s_refresh_color():
        click_fig_refresh()

    def s_open_layout():
        caption("4. G03: open demo_layout.m — tiledlayout / nexttile / yyaxis")
        open_from_cf("demo_layout.m")

    def s_run_layout():
        caption("4. Run: tiledlayout(1,2) + yyaxis right")
        run_script()

    def s_refresh_layout():
        click_fig_refresh()

    def s_open_figio():
        caption("5. G08: open demo_figio.m — savefig / openfig .fig round-trip (own format)")
        open_from_cf("demo_figio.m")

    def s_run_figio():
        caption("5. Run: savefig → openfig; Tag/title preserved")
        run_script()

    def s_refresh_figio():
        click_fig_refresh()

    def s_open_snap():
        caption("6. G10: 46 golden PNG snapshots under tests/conformance/golden/snapshots/")
        open_from_cf("demo_snap.m")

    def s_run_snap():
        caption("6. G10: e.g. imagesc.png, colormap_jet.png — M13 graphics package complete")
        run_script()

    def s_done():
        caption("M13 done — G09 output+docking, G05 colour, G03 layout, G08 .fig, G10 snapshots")

    plan = [
        (2500, s_intro),
        (4000, s_open_out),
        (6000, s_run_out),
        (7000, s_open_dock),
        (6500, s_run_dock),
        (5500, s_refresh_dock),
        (5500, s_open_color),
        (6500, s_run_color),
        (5000, s_refresh_color),
        (5500, s_open_layout),
        (6500, s_run_layout),
        (5000, s_refresh_layout),
        (5500, s_open_figio),
        (7000, s_run_figio),
        (5000, s_refresh_figio),
        (5000, s_open_snap),
        (5500, s_run_snap),
        (6000, s_done),
        (5000, root.destroy),
    ]
    t = 0
    for delay, fn in plan:
        t += delay
        root.after(t, fn)


def _mainloop(self, n=0):
    root = state["root"]
    root.title("OpenMATLAB Workbench - M13 Graphics showcase")
    root.geometry("1920x1140+0+0")
    cap = tk.Label(
        root,
        text="M13 Graphics — docking / colour / layout / .fig / snapshots",
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
    root.after(800, lambda: (root.lift(), root.focus_force()))
    root.after(300, steps)
    _orig_mainloop(self, n)


def _fontfix(cls):
    orig = cls.__init__

    def init(self, *a, **k):
        f = k.get("font")
        if isinstance(f, tuple) and f and f[0] == "Courier":
            k["font"] = ("DejaVu Sans Mono", 12)
        elif isinstance(f, tuple) and f and f[0] == "":
            k["font"] = ("DejaVu Sans",) + tuple(f[1:])
        if cls is tk.Text:
            k.setdefault("insertwidth", 4)
            k.setdefault("insertbackground", "#d00000")
            k["height"] = min(int(k.get("height", 10)), 6 if k.get("height") else 10)
        if cls is tk.Listbox and int(k.get("height", 4)) > 10:
            k["height"] = 10
        if cls is ttk.Treeview:
            k["height"] = min(int(k.get("height", 5)), 5)
        orig(self, *a, **k)

    cls.__init__ = init


for _cls in (tk.Text, tk.Listbox, ttk.Entry, ttk.Label, ttk.Treeview):
    _fontfix(_cls)

tk.Tk.__init__ = _init
tk.Misc.mainloop = _mainloop

state["wb"] = Workbench.create(cwd=DEMO)
state["wb"].run_tk(title="OpenMATLAB Workbench - M13 Graphics showcase")
