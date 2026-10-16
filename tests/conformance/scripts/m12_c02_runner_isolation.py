"""M12 C02 - runner: subprocess sandbox, timeout, stdin isolation, JSON result; one bad script does not affect others."""

from pathlib import Path

from openmatlab.qa.corpus import runner


def run(tmp: Path) -> dict:
    files = {"ok.m": "x = 1 + 1; disp(x)\n", "hang.m": "while true\nend\n", "err.m": "error('my:id','boom');\n",
             "stdin.m": "s = input('', 's');\n", "after.m": "disp(42)\n"}
    for name, src in files.items():
        (tmp / name).write_text(src)
    res = {r.name: r for r in runner.run_many([tmp / n for n in files], timeout=3)}
    return {
        "r1": int(res["ok.m"].status == "pass" and res["ok.m"].stdout.strip() == "2"),
        "r2": int(res["hang.m"].status == "timeout"),
        "r3": int(res["err.m"].status == "error" and res["err.m"].error_id == "my:id"),
        "r4": int(res["stdin.m"].status in {"error", "pass"} and res["stdin.m"].elapsed < 3),
        "r5": int(res["after.m"].status == "pass"),
        "r6": int(all(r.to_json()["name"] == r.name for r in res.values())),
    }
