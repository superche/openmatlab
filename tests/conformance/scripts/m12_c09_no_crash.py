"""M12 C09 - no internal-crash (Python traceback) in the committed full-run results."""

from pathlib import Path

from openmatlab.qa.corpus import report


def run(tmp: Path) -> dict:
    r = report.load_results()
    return {"n1": int(r.full_run), "n2": int(r.count("internal-crash") == 0)}
