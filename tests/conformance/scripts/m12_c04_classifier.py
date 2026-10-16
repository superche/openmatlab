"""M12 C04 - root-cause classifier: >=90% accuracy on >=60 labelled failures; internal-crash recall 100%."""

from pathlib import Path

from openmatlab.qa.corpus import classify


def run(tmp: Path) -> dict:
    s = classify.evaluate_labelled_set()
    return {"k1": int(s.n >= 60), "k2": int(s.accuracy >= 0.90), "k3": int(s.crash_recall == 1.0)}
