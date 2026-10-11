"""CLI and REPL for OpenMATLAB."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from openmatlab import __version__
from openmatlab.evaluator import EvalError, Evaluator, format_number, run
from openmatlab.lexer import LexerError
from openmatlab.parser import ParseError


def _print_result(value: float | None) -> None:
    if value is not None:
        print(format_number(value))


def run_source(source: str, evaluator: Evaluator | None = None) -> int:
    """Evaluate source; print result. Return exit code."""
    try:
        if evaluator is None:
            result, _ = run(source)
            _print_result(result)
        else:
            from openmatlab.parser import parse

            stmts = parse(source)
            result = evaluator.eval_program(stmts)
            _print_result(result)
        return 0
    except (LexerError, ParseError, EvalError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def repl() -> int:
    """Interactive read-eval-print loop."""
    print(f"OpenMATLAB {__version__} — clean-room MATLAB-like subset (scalars)")
    print("Type expressions or assignments. Empty line or Ctrl-D to exit.")
    evaluator = Evaluator()
    while True:
        try:
            line = input(">> ")
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            break
        if not line.strip():
            continue
        run_source(line, evaluator)
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="openmatlab",
        description="OpenMATLAB: clean-room MATLAB-compatible subset evaluator",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"openmatlab {__version__}",
    )
    parser.add_argument(
        "-e",
        "--eval",
        metavar="CODE",
        help="Evaluate a one-liner and exit",
    )
    parser.add_argument(
        "script",
        nargs="?",
        help="Path to a .m / script file to evaluate",
    )
    args = parser.parse_args(argv)

    if args.eval is not None:
        sys.exit(run_source(args.eval))

    if args.script is not None:
        path = Path(args.script)
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"error: cannot read {path}: {exc}", file=sys.stderr)
            sys.exit(1)
        sys.exit(run_source(source))

    sys.exit(repl())


if __name__ == "__main__":
    main()
