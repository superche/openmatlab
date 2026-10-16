"""Scripted GUI driver for the M11 D10 end-to-end capture (Epic #703 / #751).

Launches the real tk Workbench (``Workbench.run_tk``) at large scale and drives it
with real X pointer/keyboard events (xdotool) on the live widgets: Current Folder
open, gutter breakpoint, Run, Step In/Step, Variables editor, Stack selector,
Continue, Run Section, Run and Advance, error hyperlink. A caption bar names each
step. Used by ``record_d10_showcase.sh``; not part of the test suite.
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
SCRIPT = """%% Setup
n = 4;
v = 1:n;
%% Compute
s = scale_vec(v, 3);
total = sum(s);
%% Report
fprintf('total = %d\\n', total);
"""
FUNC = """function out = scale_vec(v, k)
  w = v * k;
  out = w + 1;
end
"""
BAD = """function bad_d10()
  x = 1;
  error('d10:e', 'oops: bad input');
end
"""

DEMO.mkdir(parents=True, exist_ok=True)
for p in DEMO.glob("*.m"):
    p.unlink()
(DEMO / "demo_d10.m").write_text(SCRIPT)
(DEMO / "scale_vec.m").write_text(FUNC)
(DEMO / "bad_d10.m").write_text(BAD)

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


def editor_text():
    state["root"].update_idletasks()
    wb = state["wb"]
    i = wb.documents.active_index
    tabs = [w for w in walk(state["root"]) if isinstance(w, tk.Text) and w.cget("cursor") != "hand2"
            and w.winfo_parent().split(".")[-1] and isinstance(w.master.master, ttk.Notebook)]
    return tabs[i] if 0 <= i < len(tabs) else None


def click_text_line(txt, line, col_x=None):
    txt.see(f"{line}.0")
    txt.update_idletasks()
    bb = txt.bbox(f"{line}.0")
    x = txt.winfo_rootx() + (col_x if col_x is not None else bb[0] + 40)
    click_at(x, txt.winfo_rooty() + bb[1] + bb[3] // 2)


def steps():
    root = state["root"]
    cf_list = find(lambda w: isinstance(w, tk.Listbox) and w.winfo_height() > 300)
    ws_tree = find(lambda w: isinstance(w, ttk.Treeview))
    stack_box = find(lambda w: isinstance(w, ttk.Combobox))
    cw_out = find(lambda w: isinstance(w, tk.Text) and w.tag_cget("errlink", "underline"))
    entry = find(lambda w: isinstance(w, ttk.Entry) and not isinstance(w, ttk.Combobox)
                 and w.winfo_rooty() > 700)

    def s_open():
        caption("1. Open demo_d10.m from Current Folder (double-click)")
        items = list(cf_list.get(0, "end"))
        i = next(k for k, s in enumerate(items) if s.endswith("demo_d10.m"))
        bb = cf_list.bbox(i)
        click_at(cf_list.winfo_rootx() + bb[0] + 60, cf_list.winfo_rooty() + bb[1] + bb[3] // 2, n=2)

    def s_bp():
        caption("2. Click the gutter on line 5 to set a breakpoint")
        txt = editor_text()
        g = txt.master.winfo_children()[0]
        bb = g.bbox("5.0")
        click_at(g.winfo_rootx() + 20, g.winfo_rooty() + bb[1] + bb[3] // 2)

    def s_run():
        caption("3. Run: execution pauses at the breakpoint (line 5, K>> prompt)")
        click_widget(button("Run"))

    def s_stepin():
        caption("4. Step In: enter scale_vec, current line marker on line 2")
        click_widget(button("Step In"))

    def s_step():
        caption("5. Step: advance to line 3 of scale_vec")
        click_widget(button("Step"))

    def s_var():
        caption("6. Inspect variable w in the Variables editor (double-click in Workspace)")
        for iid in ws_tree.get_children():
            if ws_tree.item(iid, "text") == "w":
                ws_tree.see(iid)
                ws_tree.update_idletasks()
                x, y, wd, ht = ws_tree.bbox(iid)
                click_at(ws_tree.winfo_rootx() + x + 30, ws_tree.winfo_rooty() + y + ht // 2, n=2)
                return

    def s_stack_open():
        caption("7. Stack selector: switch to the caller frame demo_d10")
        click_widget(stack_box)

    def s_stack_pick(idx):
        def f():
            vals = list(stack_box["values"])
            if idx < len(vals):
                # close dropdown and select via the combobox's own event
                xdo("key", "Escape")
                stack_box.set(vals[idx])
                stack_box.event_generate("<<ComboboxSelected>>")
                caption(f"7. Stack selector: frame '{vals[idx]}' selected (workspace follows frame)")
        return f

    def s_cont():
        caption("8. Continue: run to completion, prompt back to >>")
        click_widget(button("Continue"))

    def s_tab():
        caption("9. Switch back to the demo_d10.m editor tab")
        nb = next(w for w in walk(root) if isinstance(w, ttk.Notebook) and any(
            t.endswith("demo_d10.m") for t in (w.tab(i, "text") for i in w.tabs())))
        nb.update_idletasks()
        for x in range(5, nb.winfo_width(), 6):
            try:
                i = nb.index(f"@{x},12")
            except tk.TclError:
                continue
            if nb.tab(i, "text").endswith("demo_d10.m"):
                click_at(nb.winfo_rootx() + x + 25, nb.winfo_rooty() + 12)
                return

    def s_clear_bp():
        caption("9. Click the gutter again to clear the breakpoint")
        txt = editor_text()
        g = txt.master.winfo_children()[0]
        bb = g.bbox("5.0")
        click_at(g.winfo_rootx() + 20, g.winfo_rooty() + bb[1] + bb[3] // 2)

    def s_clear():
        caption("10. Code sections: clear the workspace first (clear all)")
        click_widget(entry)
        time.sleep(0.2)
        xdo("type", "--delay", 90, "clear all")
        xdo("key", "Return")

    def s_caret():
        caption("10. Code sections: place caret in section 'Setup' (line 2)")
        click_text_line(editor_text(), 2)

    def s_runsec():
        caption("10. Run Section: only the %% Setup section runs (n, v appear)")
        click_widget(button("Run Section"))

    def s_adv():
        caption("11. Run and Advance: run section, caret jumps to next section")
        click_widget(button("Run and Advance"))

    def s_adv2():
        caption("11. Run and Advance again: section 'Compute' runs")
        click_widget(button("Run and Advance"))

    def s_err():
        caption("12. Call a function that errors: bad_d10()")
        click_widget(entry)
        time.sleep(0.2)
        xdo("type", "--delay", 90, "bad_d10()")

    def s_err_enter():
        xdo("key", "Return")

    def s_link():
        caption("13. Click the 'Error in bad_d10 (line 3)' hyperlink")
        rng = cw_out.tag_ranges("errlink")
        if not rng:
            caption("13. (no error link found)")
            return
        start = str(rng[-2])
        cw_out.see(start)
        cw_out.update_idletasks()
        bb = cw_out.bbox(f"{start}+8c")
        click_at(cw_out.winfo_rootx() + bb[0] + 4, cw_out.winfo_rooty() + bb[1] + bb[3] // 2)

    def s_done():
        caption("Editor opened bad_d10.m with caret on line 3  -  D10 end-to-end flow complete")

    plan = [
        (2500, s_open), (4500, s_bp), (4000, s_run), (5000, s_stepin), (4500, s_step),
        (4500, s_var), (5000, s_stack_open), (1500, s_stack_pick(1)), (4500, s_stack_pick(0)),
        (4000, s_cont), (4000, s_tab), (3000, s_clear_bp), (3500, s_clear), (4000, s_caret), (3000, s_runsec), (4500, s_adv),
        (4500, s_adv2), (5000, s_err), (2500, s_err_enter), (3500, s_link), (3000, s_done),
        (6000, root.destroy),
    ]
    t = 0
    for delay, fn in plan:
        t += delay
        root.after(t, fn)


def _mainloop(self, n=0):
    root = state["root"]
    root.title("OpenMATLAB Workbench - M11 D10 end-to-end")
    root.geometry("1920x1140+0+0")
    cap = tk.Label(root, text="M11 D10 - Debugger and Workbench workflows",
                   font=("DejaVu Sans", 15, "bold"), bg="#1f3a5f", fg="white", anchor="w", padx=12, pady=6)
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
state["wb"].run_tk(title="OpenMATLAB Workbench - M11 D10 end-to-end")
