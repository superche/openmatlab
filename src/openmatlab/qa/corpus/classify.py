"""Rule-based root-cause classifier for corpus failures (M12 C04, Epic #763).

``classify(result, code, siblings)`` maps one failed run to ``(category, key)``:

==================== ===============================================================
``internal-crash``   Python exception or traceback inside OpenMATLAB (always p0)
``timeout``          wall-clock budget exceeded
``corpus-noise``     the sample is not a runnable MATLAB program (Octave/Scilab dialect,
                     prose or output left in the code, fragment relying on undefined
                     context, helper defined elsewhere); excluded from pass rates
``toolbox:<tb>``     needs a MathWorks toolbox or third-party package
``io-env``           files, network, OS, interactive input
``graphics``         a graphics call is missing or fails (key = function)
``missing-builtin``  a MATLAB base function is not implemented (key = name)
``parse-error``      valid MATLAB that OpenMATLAB cannot parse (key = token)
``semantics-diff``   valid MATLAB that runs differently (runtime error or T2/T3 mismatch)
==================== ===============================================================

Rules only (error id, message patterns, name lists); deterministic, no network, no LLM.
"""

from __future__ import annotations

import re
from typing import Iterable, Optional, Tuple

CATEGORIES = ("internal-crash", "timeout", "corpus-noise", "toolbox", "io-env", "graphics",
              "missing-builtin", "parse-error", "semantics-diff")
EXCLUDED_ALWAYS = ("corpus-noise",)
EXCLUDED_T1 = ("corpus-noise", "toolbox", "io-env")

# Octave / Scilab / FreeMat functions that are not MATLAB: a script calling them is dialect noise.
DIALECT_FUNCS = {
    "printf", "puts", "fputs", "fdisp", "mprintf", "mfprintf", "scanf", "disp_", "endfunction", "columns",
    "rows", "postpad", "prepad", "index", "rindex", "strvcat_", "do_string_escapes", "num2str_", "lookup",
    "printf_", "ifelse", "merge", "fflush_", "stdout", "stderr", "nthargout", "print_usage", "inputname_",
    "isargout", "validatestring_", "mat2str_", "typecast_", "sizemax", "idivide_", "deal_", "polyout",
    "mtimes_", "getenv_", "kbhit", "usleep", "exist_", "sum_", "isrow_", "strjust_", "cellfun_",
    "evalin_", "toc_", "tic_", "argv", "program_name", "OCTAVE_VERSION", "pkg", "graphics_toolkit",
    "unwind_protect", "end_unwind_protect", "func2str_", "factor_", "primes_", "isprime_",
}

TOOLBOXES = {
    "symbolic": {"sym", "syms", "vpa", "digits", "simplify", "subs", "symsum", "solve", "dsolve", "diff_sym",
                 "expand", "factor_sym", "limit", "taylor", "int_sym", "symvar", "vpi", "pretty", "latex"},
    "statistics": {"normrnd", "normpdf", "normcdf", "norminv", "binopdf", "binornd", "poissrnd", "unifrnd",
                   "randsample", "pdist", "squareform", "linkage", "kmeans", "fitdist", "tabulate", "nanmean",
                   "nanmax", "nanmin", "nansum", "prctile", "quantile", "iqr", "zscore", "ttest", "chi2gof",
                   "geomean", "harmmean", "skewness", "kurtosis", "range", "mad", "exprnd", "randg"},
    "image": {"imresize", "rgb2gray", "edge", "imfilter", "imrotate", "im2bw",
              "bwlabel", "imerode", "imdilate", "fspecial", "imadjust", "imcrop", "imnoise", "medfilt2",
              "regionprops", "padarray", "im2double", "im2uint8", "graythresh", "imbinarize", "imhist"},
    "signal": {"butter", "cheby1", "filtfilt", "freqz", "hamming", "hann", "periodogram", "pwelch", "resample",
               "xcorr", "findpeaks", "spectrogram", "chirp", "sawtooth", "square", "upsample", "downsample"},
    "optimization": {"fminunc", "fmincon", "linprog", "intlinprog", "quadprog", "lsqnonlin", "lsqcurvefit",
                     "optimoptions", "ga", "particleswarm", "fsolve"},
    "communications": {"de2bi", "bi2de", "gf", "awgn", "randi_", "qammod", "pskmod"},
    "fixed-point": {"fi", "numerictype", "fimath"},
    "java": {"com", "java", "javaObject", "javaMethod", "javaArray", "javaaddpath"},
    "dotnet": {"NET", "System"},
    "database": {"database", "fetch", "exec"},
    "parallel": {"parpool", "gcp", "spmd", "labindex", "numlabs", "gpuArray", "gather"},
    "mapping": {"geoshow", "worldmap", "distance", "deg2km", "km2deg"},
}
_TOOLBOX_OF = {f: tb for tb, fs in TOOLBOXES.items() for f in fs}

# Only functions whose effect needs something the sandbox withholds (shell, network, GUI dialogs,
# devices). A missing base function that merely touches files (getenv, mkdir, dir...) is missing-builtin.
IO_ENV_FUNCS = {"system", "dos", "unix", "urlread", "urlwrite", "webread", "webwrite", "websave", "ftp", "open",
                "winopen", "web", "clipboard", "uigetfile", "uiputfile", "inputdlg", "questdlg", "msgbox",
                "waitforbuttonpress", "uiwait", "tcpip", "udp", "serial", "audiorecorder", "sound", "soundsc",
                "audioplayer", "beep", "actxserver", "listdlg", "errordlg", "warndlg", "helpdlg"}

GRAPHICS_FUNCS = {
    "plot", "plot3", "figure", "axes", "axis", "subplot", "hold", "line", "patch", "surf", "surface", "mesh",
    "meshc", "surfc", "contour", "contourf", "contour3", "quiver", "quiver3", "bar", "bar3", "barh", "barh3",
    "pie", "pie3", "hist", "histogram", "histogram2", "area", "fill", "fill3", "scatter", "scatter3", "stem",
    "stairs", "errorbar", "polar", "polarplot", "rose", "compass", "feather", "image", "imagesc", "colormap",
    "colorbar", "caxis", "clim", "shading", "lighting", "light", "material", "camlight", "view", "rotate3d",
    "zoom", "pan", "rectangle", "annotation", "text", "title", "xlabel", "ylabel", "zlabel", "legend",
    "grid", "box", "xlim", "ylim", "zlim", "drawnow", "getframe", "movie", "im2frame", "frame2im", "print",
    "saveas", "savefig", "openfig", "gcf", "gca", "gco", "clf", "cla", "close", "set", "get_", "ishandle",
    "isgraphics", "uicontrol", "uimenu", "uipanel", "uitable", "uifigure", "linkaxes", "daspect", "pbaspect",
    "fplot", "ezplot", "ezsurf", "fsurf", "fmesh", "fcontour", "fimplicit", "loglog", "semilogx", "semilogy",
    "yyaxis", "plotyy", "sphere", "cylinder", "ellipsoid", "peaks_", "waterfall", "ribbon", "slice",
    "isosurface", "streamline", "comet", "comet3", "animatedline", "addpoints", "spy", "pcolor", "trisurf",
    "trimesh", "triplot", "voronoi", "delaunay_", "hgtransform", "makehgtform", "copyobj", "findobj",
    "allchild", "ancestor", "refresh", "rgbplot", "hsv2rgb_", "rgb2hsv_", "parula", "jet", "hot", "gray",
    "bone", "copper", "pink", "lines", "turbo", "colororder", "ind2rgb", "image_", "imfinfo", "camva",
    "campos", "camtarget", "camup", "camzoom", "camorbit", "axis_", "datetick", "ginput_", "gtext",
    "histogram_", "heatmap", "imshow", "wordcloud", "geoplot", "boxplot", "graph_plot", "colorbar_",
}

_UNDEF = re.compile(r"Undefined (?:function or variable|function|variable)[^:']*[:']\s*'?([A-Za-z_]\w*)")
_UNDEF_VAR = re.compile(r"^Undefined variable:?\s*'?([A-Za-z_]\w*)")
_IO_MSG = re.compile(r"(fopen|file identifier|Unable to find or open|No such file|input: no more input|"
                     r"Unable to read|cannot open|end of input|permission denied|network|URL)", re.I)
_DIALECT_SYNTAX = [
    (re.compile(r"^\s*#(?![{}])", re.M), "octave-comment"),
    (re.compile(r"\bend(function|for|while|if|switch|_try_catch)\b"), "octave-end"),
    (re.compile(r"(\+\+|--)\s*;|[^=!<>~]\b\s*(\+=|-=|\*=|/=)"), "octave-assign-op"),
    (re.compile(r"!=|!\s*[A-Za-z(]"), "octave-not"),
    (re.compile(r"\bunwind_protect\b|\bdo\b\s*$|\buntil\b", re.M), "octave-block"),
    (re.compile(r"\bprintf\s*\(|\bputs\s*\(|\bfdisp\s*\("), "octave-io"),
    (re.compile(r"^\s*//|\s//\s", re.M), "scilab-comment"),
    (re.compile("[\u2018\u2019\u201c\u201d]"), "smart-quotes"),
    (re.compile(r"\bmprintf\b|\bdeff\b|\bendfunction\b"), "scilab"),
]
_PROSE = re.compile(r"^\s*(ans|[A-Za-z_]\w*)\s*=\s*$|^\s*Columns? \d+|^\s*Output:|^\s*Result:|^\s*(The|This|Sample|Example) \w+",
                    re.M)


def dialect_marker(code: str) -> str:
    for rx, key in _DIALECT_SYNTAX:
        if rx.search(_without_strings(code)):
            return key
    return ""


def _without_strings(code: str) -> str:
    out = []
    for ln in code.splitlines():
        ln = re.sub(r'"[^"\n]*"', '""', ln)
        ln = re.sub(r"(?<![\w)\]}.'])'(?:[^'\n]|'')*'", "''", ln)
        if not ln.lstrip().startswith("#"):
            ln = re.sub(r"%.*$", "", ln)
        out.append(ln)
    return "\n".join(out)


def _defined_functions(code: str) -> set:
    return set(re.findall(r"^\s*function\s+(?:\[[^\]]*\]\s*=\s*|\w+\s*=\s*)?([A-Za-z_]\w*)", code, re.M))


def _assigned(code: str) -> set:
    names = set(re.findall(r"^\s*([A-Za-z_]\w*)\s*(?:\([^=]*\))?\s*=(?!=)", code, re.M))
    for grp in re.findall(r"^\s*\[([^\]]*)\]\s*=(?!=)", code, re.M):
        names.update(re.findall(r"[A-Za-z_]\w*", grp))
    names.update(re.findall(r"^\s*(?:for|parfor)\s*\(?\s*([A-Za-z_]\w*)\s*=", code, re.M))
    names.update(re.findall(r"function\s+[^\n]*\(([^)]*)\)", code))
    return names


def features(code: str, siblings: Iterable[str] = (), resolvable: Optional[dict] = None) -> dict:
    """The code facts the rules use (identifiers and flags only, never code bodies).

    Stored with each labelled failure so the classifier can be evaluated offline in CI.
    """
    clean = _without_strings(code)
    return {
        "dialect": dialect_marker(code),
        "prose": bool(_PROSE.search(code)),
        "interactive": bool(re.search(r"\b(input|keyboard|pause|waitforbuttonpress|ginput)\b", clean)),
        "defined": sorted(_defined_functions(code)),
        "assigned": sorted(_assigned(code)),
        "siblings": sorted(set(siblings)),
        "resolvable": dict(sorted((resolvable or {}).items())),  # undefined name -> where its file sits
    }


def classify(result: dict, code: str = "", siblings: Iterable[str] = ()) -> Tuple[str, str]:
    """Return ``(category, key)`` for one failed run; ``("pass", "")`` for a pass."""
    return classify_features(result, features(code, siblings))


def classify_features(result: dict, f: dict) -> Tuple[str, str]:
    """Rules over a run result and :func:`features`; see the module docstring for the categories."""
    status, kind = result.get("status", ""), result.get("kind", "")
    msg = result.get("message", "") or ""
    eid = result.get("error_id", "") or ""
    if status == "pass":
        return "pass", ""
    if status == "crash" or kind == "internal" or "Traceback (most recent call last)" in (result.get("stderr") or ""):
        return "internal-crash", (msg.split(":", 1)[0] or "crash").strip()[:60]
    if status == "timeout":
        return ("io-env", "interactive") if f["interactive"] else ("timeout", "")
    if kind == "output-limit":
        return "timeout", "output-limit"
    dialect = f["dialect"]
    if kind == "parse":
        if dialect:
            return "corpus-noise", dialect
        if f["prose"]:
            return "corpus-noise", "prose-or-output"
        m = re.search(r"(?:Unexpected token|got) (\w+)", msg) or re.search(r"Unexpected character '(.)'", msg)
        return "parse-error", (m.group(1) if m else re.sub(r"\s+at line \d+.*$", "", msg)[:60])
    if eid == "MATLAB:recursionLimit" or "recursion limit" in msg.lower():
        return "semantics-diff", "recursionLimit"
    defined, assigned = set(f["defined"]), set(f["assigned"])
    m = _UNDEF.search(msg)
    if m:
        name = m.group(1)
        if name in DIALECT_FUNCS or (dialect and name in {"printf", "puts", "fdisp", "mprintf", "disp"}):
            return "corpus-noise", "dialect:" + name
        if name in _TOOLBOX_OF:
            return "toolbox:" + _TOOLBOX_OF[name], name
        if name in IO_ENV_FUNCS:
            return "io-env", name
        if name in GRAPHICS_FUNCS:
            return "graphics", name
        where = f.get("resolvable", {}).get(name)
        if where:  # the source tree ships the function, so OpenMATLAB failed to resolve it
            return "semantics-diff", "function-resolution:" + where
        if name in set(f["siblings"]) and name not in defined:
            return "corpus-noise", "missing-dependency"
        if name in assigned or name in defined:
            return "semantics-diff", "undefined-variable"
        if _UNDEF_VAR.match(msg):
            return "corpus-noise", "fragment"
        x2y = re.fullmatch(r"[a-z]+2[a-z]+", name)  # dec2base, num2cell: MATLAB naming, not a user helper
        if name[:1].isupper() or re.search(r"[A-Z]", name[1:]) or "_" in name or (re.search(r"\d", name) and not x2y):
            return "corpus-noise", "missing-dependency"  # camelCase/user-style helper published elsewhere
        return "missing-builtin", name
    if _IO_MSG.search(msg):
        return "io-env", "input" if "input" in msg else "file"
    if dialect:
        return "corpus-noise", dialect
    if re.search(r"graphics|axes|figure|handle|colormap|Line|Patch|Surface", msg) or eid.startswith(("MATLAB:hg", "MATLAB:graphics")):
        m = re.search(r"\b(%s)\b" % "|".join(sorted(GRAPHICS_FUNCS, key=len, reverse=True)), msg)
        return "graphics", (m.group(1) if m else "property")
    key = re.sub(r"'[^']*'|\"[^\"]*\"|\d+", "_", msg).strip()[:60]
    return "semantics-diff", key or eid or "error"


def top(category: str) -> str:
    return category.split(":", 1)[0]


class LabelStats:
    def __init__(self, rows):
        self.rows = rows  # (id, label, predicted)
        self.n = len(rows)
        self.correct = sum(top(p) == top(lab) for _i, lab, p in rows)
        self.accuracy = self.correct / max(1, self.n)
        crashes = [(lab, p) for _i, lab, p in rows if lab == "internal-crash"]
        self.crash_recall = sum(p == "internal-crash" for _l, p in crashes) / max(1, len(crashes)) if crashes else 0.0
        self.errors = [(i, lab, p) for i, lab, p in rows if top(p) != top(lab)]


def evaluate_labelled_set(path=None) -> LabelStats:
    """Score the classifier on ``corpus/labels.json`` (offline: stored results + features)."""
    import json

    from .manifest import corpus_dir

    doc = json.loads((path or corpus_dir() / "labels.json").read_text(encoding="utf-8"))
    return LabelStats([(x["id"], x["label"], classify_features(x["result"], x["features"])[0]) for x in doc["labels"]])
