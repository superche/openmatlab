"""M12 C03 - deterministic preprocessing: transcript de-prompting, function-file detection, input fixtures; noise <= 10%."""

from pathlib import Path

from openmatlab.qa.corpus import preprocess


def run(tmp: Path) -> dict:
    t = preprocess.normalize(">> a = 2+3\n\na =\n\n     5\n\n>> b = a*2\n")
    f = preprocess.normalize("function y = f(x)\ny = x;\nend\n")
    i = preprocess.normalize("n = input('n? ');\ndisp(n)\n")
    return {
        "p1": int(t.kind == "script" and "a = 2+3" in t.code and ">>" not in t.code and t.expected_stdout is not None),
        "p2": int(f.kind == "function"),
        "p3": int(i.stdin_fixture is not None),
        "p4": int(preprocess.pilot_noise_rate() <= 0.10),
    }
