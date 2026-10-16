"""Failure groups and deduplicated ``corpus`` issue filing (M12 C10, Epic #764).

``group(records)`` collapses failures by ``(category, key)``. ``file_issues(groups)`` opens one
GitHub issue labelled ``corpus`` per group that has no issue yet; the dedup marker
``corpus-group: <category>|<key>`` sits in the issue body and is searched in every state, so a
group is filed once, ever. Filing uses the ``gh`` CLI and is opt-in (``triage --file``).
"""

from __future__ import annotations

import json
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence

NOT_FAILURES = ("pass", "deferred", "corpus-noise", "")
LABEL = "corpus"
P0 = ("internal-crash",)


@dataclass
class Group:
    category: str
    key: str
    ids: List[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.ids)

    @property
    def marker(self) -> str:
        return f"corpus-group: {self.category}|{self.key}"

    @property
    def title(self) -> str:
        return f"[corpus] {self.category}: {self.key[:90]} ({self.count} entr{'y' if self.count == 1 else 'ies'})"

    def body(self) -> str:
        ex = "\n".join(f"- `{i}`" for i in self.ids[:20])
        more = f"\n- ... and {self.count - 20} more" if self.count > 20 else ""
        return (f"Auto-filed by `python -m openmatlab.qa.corpus triage --file` from `docs/corpus/results.json` "
                f"(M12, Epic #764).\n\nCategory: `{self.category}`\nKey: `{self.key}`\nEntries: {self.count}\n\n"
                f"{ex}{more}\n\nReproduce: `python -m openmatlab.qa.corpus fetch && python -m openmatlab.qa.corpus run`.\n\n"
                f"<!-- {self.marker} -->\n")


def group(records: Sequence[dict]) -> List[Group]:
    """Failure groups sorted by size (desc), then category and key."""
    acc: Dict[tuple, Group] = {}
    for r in records:
        cat = r.get("category", "") or ""
        if r.get("status") in ("pass", "n/a") or cat.split(":", 1)[0] in NOT_FAILURES:
            continue
        k = (cat, str(r.get("key", "") or ""))
        acc.setdefault(k, Group(*k)).ids.append(str(r.get("id", r.get("name", ""))))
    gs = list(acc.values())
    for g in gs:
        g.ids.sort()
    return sorted(gs, key=lambda g: (-g.count, g.category, g.key))


def _gh(args: List[str]) -> str:
    try:
        p = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"gh failed: {exc}") from None
    if p.returncode:
        raise RuntimeError(f"gh {' '.join(args[:2])}: {p.stderr.strip()[:200]}")
    return p.stdout


def existing_markers(gh: Callable[[List[str]], str] = _gh) -> Dict[str, int]:
    """Dedup markers of every ``corpus`` issue (open or closed) -> issue number."""
    out = gh(["issue", "list", "--label", LABEL, "--state", "all", "--limit", "1000", "--json", "number,body"])
    found = {}
    for it in json.loads(out or "[]"):
        for line in (it.get("body") or "").splitlines():
            line = line.strip()
            if line.startswith("<!-- corpus-group: "):
                found[line[5:-4].strip()] = it["number"]
    return found


def file_issues(groups: Sequence[Group], *, min_count: int = 1, limit: int = 50, dry_run: bool = False,
                milestone: Optional[str] = None, gh: Callable[[List[str]], str] = _gh) -> List[tuple]:
    """File new groups; returns ``[(group, issue-or-None, action)]`` with action ``filed|exists|would-file``."""
    have = existing_markers(gh)
    done = []
    for g in groups:
        if g.count < min_count and g.category not in P0:
            continue
        if g.marker in have:
            done.append((g, have[g.marker], "exists"))
            continue
        if len([d for d in done if d[2] != "exists"]) >= limit:
            break
        if dry_run:
            done.append((g, None, "would-file"))
            continue
        args = ["issue", "create", "--title", g.title, "--body", g.body(), "--label", LABEL]
        if g.category in P0:
            args += ["--label", "p0"]
        if milestone:
            args += ["--milestone", milestone]
        url = gh(args).strip().splitlines()[-1]
        num = int(url.rsplit("/", 1)[-1]) if url.rsplit("/", 1)[-1].isdigit() else None
        have[g.marker] = num
        done.append((g, num, "filed"))
    return done
