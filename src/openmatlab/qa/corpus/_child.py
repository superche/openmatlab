"""Sandboxed child: run one .m file in a fresh Session and print one JSON line (M12 C02).

Invoked by :mod:`openmatlab.qa.corpus.runner`; not a user entry point. The script's own
stdout/stderr go to the real streams; the JSON verdict is written to the file named by
``OPENMATLAB_RESULT`` so script output can never corrupt it.
"""

from __future__ import annotations

import json
import os
import sys


def main(argv) -> int:
    path, mode = argv[0], (argv[1] if len(argv) > 1 else "run")
    folder = argv[2] if len(argv) > 2 else os.path.dirname(os.path.abspath(path))
    out = {"status": "pass", "error_id": "", "message": "", "kind": ""}
    try:
        from openmatlab.host.repl import ReplSession
        from openmatlab.lang.lexer import LexerError
        from openmatlab.lang.parser import ParseError
        from openmatlab.runtime.evaluator import EvalError

        p = path.replace("'", "''")
        try:
            r = ReplSession()
            r.run_line("addpath('%s');" % folder.replace("'", "''"))
            if mode == "parse":
                from openmatlab.lang.parser import parse

                parse(open(path, encoding="utf-8", errors="replace").read())
            else:
                r.run_line(f"run('{p}');")
        except (LexerError, ParseError) as exc:
            out.update(status="error", kind="parse", message=str(exc))
        except EvalError as exc:
            out.update(status="error", kind="eval", message=str(exc), error_id=getattr(exc, "identifier", "") or "")
        except RecursionError as exc:
            out.update(status="error", kind="eval", message=f"Maximum recursion limit reached ({exc})",
                       error_id="MATLAB:recursionLimit")
    except SystemExit as exc:  # exit/quit inside a script
        out.update(status="pass" if not exc.code else "error", kind="exit", message=f"exit({exc.code})")
    except BaseException as exc:  # internal crash: report, never a traceback on the user's terminal
        out.update(status="crash", kind="internal", message=f"{type(exc).__name__}: {exc}")
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:
        pass
    res = os.environ.get("OPENMATLAB_RESULT")
    if res:
        with open(res, "w", encoding="utf-8") as fh:
            json.dump(out, fh)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
