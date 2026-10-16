"""M12 c08 - T3 pass rate on the committed full-run results meets the threshold locked in the milestone doc."""

from pathlib import Path

from openmatlab.qa.corpus import report


def run(tmp: Path) -> dict:
    r = report.load_results()
    return {"t1": int(r.full_run), "t2": int(r.rate("T3") >= report.threshold("T3"))}
