"""M13 G10 - image snapshots: >=40 golden scenes within tolerance, deterministic rendering."""

from pathlib import Path

from openmatlab.qa import snapshots


def run(tmp: Path) -> dict:
    scenes = snapshots.scenes()
    res = snapshots.check_all(tmp)
    again = snapshots.check_all(tmp / "again")
    return {"z1": int(len(scenes) >= 40), "z2": int(all(r.ok for r in res)),
            "z3": int([r.digest for r in res] == [r.digest for r in again])}
