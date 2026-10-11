"""Thin CLI — architecture status / version (no expression evaluation yet)."""

from __future__ import annotations

import argparse
import sys

from openmatlab import __version__

_STATUS = """\
OpenMATLAB {version} — architecture stage (clean-room / public specs)

Package seams:
  openmatlab.host      CLI/REPL, DisplayPolicy, PlotSurface
  openmatlab.lang      lexer/parser/AST (matrix grammar reserved)
  openmatlab.runtime   Value/Array, Workspace, FunctionResolver
  openmatlab.numerics  ArrayBackend (NumPy placeholder)
  openmatlab.graphics  GraphicsBackend (matplotlib placeholder)
  openmatlab.libs      toolbox / path placeholder

Product intent: matrix-first workbench, interactive display, functions/path,
plots seam. Expression evaluation intentionally incomplete this stage.
See docs/ARCHITECTURE.md.
"""


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="openmatlab",
        description="OpenMATLAB: matrix-first MATLAB-compatible workbench",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"openmatlab {__version__}",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print architecture package status and exit",
    )
    # Accept legacy flags so old muscle memory does not crash hard
    parser.add_argument("-e", "--eval", metavar="CODE", help=argparse.SUPPRESS)
    parser.add_argument("script", nargs="?", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.eval is not None or args.script is not None:
        print(
            "openmatlab: expression/script evaluation not wired "
            "(architecture stage). Try: openmatlab --status",
            file=sys.stderr,
        )
        sys.exit(2)

    print(_STATUS.format(version=__version__))
    sys.exit(0)


if __name__ == "__main__":
    main()
