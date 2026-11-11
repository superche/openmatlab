"""Label unsigned binaries explicitly and hash the final deliverables."""
import hashlib
import os
from pathlib import Path
import sys

for path in Path(sys.argv[1]).iterdir():
    if path.suffix not in {".exe", ".dmg"}:
        continue
    if os.environ.get("SIGNED") != "true":
        path = path.rename(path.with_name(path.stem + "-unsigned" + path.suffix))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    path.with_suffix(path.suffix + ".sha256").write_text(f"{digest}  {path.name}\n")
