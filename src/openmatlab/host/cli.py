"""CLI — QA/dev: status, features, cases, defects→gh, test→pytest."""

from __future__ import annotations

import argparse
import subprocess
import sys
from typing import List, Optional

from openmatlab import __version__

_STATUS = """\
OpenMATLAB {version} — architecture + layered QA (off-the-shelf preferred)

Packages: host · lang · runtime · numerics · graphics · libs · qa

QA layers (docs/QA.md):
  1. Features     docs/feature_map.yaml      → openmatlab features
  2. Cases        Gherkin+pytest-bdd + catalog → openmatlab cases
  3. Environments tests/{{unit,conformance,interactive}}
  4. Tooling      pytest-bdd · coverage · Actions · gh
  5. Defects      GitHub Issues (canonical)  → openmatlab defects / gh issue

Interactive UI later: Playwright/Selenium only when a web workbench exists.
Eval: openmatlab -e "..." · REPL when no args. docs/ARCHITECTURE.md
"""


def _cmd_status(_args: argparse.Namespace) -> int:
    print(_STATUS.format(version=__version__))
    return 0


def _cmd_features(args: argparse.Namespace) -> int:
    from openmatlab.qa.feature_map import load_feature_map

    fmap = load_feature_map()
    for problem in fmap.validate():
        print(f"feature_map warning: {problem}", file=sys.stderr)
    features = fmap.filter(layer=args.layer, status=args.status)
    if args.format == "yaml":
        try:
            import yaml
        except ImportError:
            print("error: PyYAML required for --format yaml", file=sys.stderr)
            return 1
        if args.layer or args.status:
            payload = {
                "filter": {"layer": args.layer, "status": args.status},
                "features": [
                    {
                        "id": f.id,
                        "layer": f.layer,
                        "name": f.name,
                        "status": f.status,
                    }
                    for f in features
                ],
            }
            print(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))
        else:
            print(fmap.format_yaml())
    else:
        print(fmap.format_table(features))
        counts = fmap.counts_by_status()
        print("counts: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    return 0


def _cmd_cases(args: argparse.Namespace) -> int:
    from openmatlab.qa.catalog import load_test_catalog
    from openmatlab.qa.feature_map import load_feature_map

    catalog = load_test_catalog()
    known = {f.id for f in load_feature_map().features}
    for problem in catalog.validate(known_feature_ids=known):
        print(f"test_catalog warning: {problem}", file=sys.stderr)
    rows = catalog.filter(
        kind=args.kind, status=args.status, env=args.env, feature=args.feature
    )
    if args.format == "yaml":
        try:
            import yaml
        except ImportError:
            print("error: PyYAML required", file=sys.stderr)
            return 1
        print(
            yaml.safe_dump(
                {
                    "use_cases": catalog.raw.get("use_cases"),
                    "test_cases": [
                        {
                            "id": t.id,
                            "kind": t.kind,
                            "status": t.status,
                            "env": t.env,
                            "title": t.title,
                            "features": t.features,
                        }
                        for t in rows
                    ],
                },
                sort_keys=False,
                allow_unicode=True,
            )
        )
    else:
        print(
            catalog.format_table(
                rows, include_use_cases=not (args.kind or args.status or args.env)
            )
        )
    return 0


def _cmd_defects(args: argparse.Namespace) -> int:
    from openmatlab.qa.defects import format_help, list_issues

    print(format_help())
    state = args.status or "open"
    # map common aliases
    if state in ("all",):
        state = "all"
    return list_issues(label=args.label, state=state)


def _cmd_test(args: argparse.Namespace) -> int:
    markers = {
        "unit": "unit",
        "conformance": "conformance",
        "interactive": "interactive",
        "all": None,
    }
    mark = markers[args.suite]
    cmd: List[str] = [sys.executable, "-m", "pytest"]
    if mark:
        cmd.extend(["-m", mark])
    if args.keyword:
        cmd.extend(["-k", args.keyword])
    if args.pytest_args:
        cmd.extend(args.pytest_args)
    print("Running:", " ".join(cmd), file=sys.stderr)
    return subprocess.call(cmd)


def _eval_code(source: str) -> int:
    """Evaluate one-liner / snippet with default Session."""
    from openmatlab.host.repl import ReplSession
    from openmatlab.lang.lexer import LexerError
    from openmatlab.lang.parser import ParseError
    from openmatlab.runtime.evaluator import EvalError

    try:
        ReplSession().run_line(source)
        return 0
    except (LexerError, ParseError, EvalError, ImportError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _run_repl() -> int:
    from openmatlab.host.repl import ReplSession
    from openmatlab.lang.lexer import LexerError
    from openmatlab.lang.parser import ParseError
    from openmatlab.runtime.evaluator import EvalError

    print(f"OpenMATLAB {__version__} — matrix-first subset (Ctrl-D to exit)")
    repl = ReplSession()
    if repl.session.numerics is None:
        print("error: NumPy required for REPL (pip install -e \".[dev]\")", file=sys.stderr)
        return 1
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
        try:
            repl.run_line(line)
        except (LexerError, ParseError, EvalError) as exc:
            print(f"error: {exc}", file=sys.stderr)
    return 0



def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="openmatlab",
        description="OpenMATLAB workbench — architecture + layered QA CLI",
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"openmatlab {__version__}"
    )
    parser.add_argument(
        "-e",
        "--eval",
        metavar="CODE",
        help="Evaluate CODE and print result (unless suppressed with ;)",
    )
    parser.add_argument("--status", action="store_true", help="Print QA/architecture status")
    parser.add_argument("--features", action="store_true", help="Dump feature map")
    parser.add_argument("--format", choices=("table", "yaml"), default="table")
    parser.add_argument("--layer", default=None)
    parser.add_argument("--status-filter", default=None, metavar="STATUS")

    sub = parser.add_subparsers(dest="command")

    p_status = sub.add_parser("status", help="Architecture + QA layer blurb")
    p_status.set_defaults(func=_cmd_status)

    p_feat = sub.add_parser("features", help="Layer 1: feature map")
    p_feat.add_argument("--format", choices=("table", "yaml"), default="table")
    p_feat.add_argument("--layer", default=None)
    p_feat.add_argument("--status", default=None)
    p_feat.set_defaults(func=_cmd_features)

    p_cases = sub.add_parser("cases", help="Layer 2: use-case / test-case catalog")
    p_cases.add_argument("--format", choices=("table", "yaml"), default="table")
    p_cases.add_argument("--kind", default=None, help="unit|conformance|interactive")
    p_cases.add_argument("--status", default=None)
    p_cases.add_argument("--env", default=None)
    p_cases.add_argument("--feature", default=None, help="Filter by feature id")
    p_cases.set_defaults(func=_cmd_cases)

    p_def = sub.add_parser(
        "defects",
        help="Layer 5: list GitHub Issues via gh (canonical tracker)",
    )
    p_def.add_argument(
        "--status",
        default="open",
        help="Issue state passed to gh (open|closed|all)",
    )
    p_def.add_argument("--label", default=None, help="Filter by GitHub label")
    p_def.set_defaults(func=_cmd_defects)

    p_test = sub.add_parser("test", help="Layer 4: run pytest by environment")
    p_test.add_argument(
        "--suite",
        choices=("unit", "conformance", "interactive", "all"),
        default="unit",
    )
    p_test.add_argument("-k", dest="keyword", default=None)
    p_test.add_argument("pytest_args", nargs="*", default=[])
    p_test.set_defaults(func=_cmd_test)

    args = parser.parse_args(argv)

    if args.eval is not None:
        sys.exit(_eval_code(args.eval))

    if args.command and getattr(args, "func", None):
        sys.exit(args.func(args))

    if args.features:
        ns = argparse.Namespace(
            format=args.format, layer=args.layer, status=args.status_filter
        )
        sys.exit(_cmd_features(ns))

    if args.status:
        sys.exit(_cmd_status(args))

    # No subcommand: interactive REPL
    sys.exit(_run_repl())


if __name__ == "__main__":
    main()
