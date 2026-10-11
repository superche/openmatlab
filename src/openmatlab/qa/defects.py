"""Layer 5 bridge: prefer GitHub Issues via `gh` (no in-repo defect DB)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from typing import List, Optional


def gh_available() -> bool:
    return shutil.which("gh") is not None


def format_help() -> str:
    return """\
OpenMATLAB defects → GitHub Issues (canonical)

  gh issue list
  gh issue list --label gap
  gh issue create
  # templates: .github/ISSUE_TEMPLATE/ (bug, gap)
  # include feature_ids from docs/feature_map.yaml
  # include case_ids from docs/test_catalog.yaml

See docs/WORKFLOW.md and docs/defects/README.md
"""


def list_issues(
    *,
    label: Optional[str] = None,
    state: str = "open",
    limit: int = 20,
) -> int:
    """Run `gh issue list`. Return process exit code (127 if gh missing)."""
    if not gh_available():
        print(format_help(), file=sys.stderr)
        print(
            "error: `gh` not found on PATH; install GitHub CLI or use the web UI",
            file=sys.stderr,
        )
        return 127
    cmd: List[str] = [
        "gh",
        "issue",
        "list",
        "--state",
        state,
        "--limit",
        str(limit),
    ]
    if label:
        cmd.extend(["--label", label])
    print("Running:", " ".join(cmd), file=sys.stderr)
    return subprocess.call(cmd)
