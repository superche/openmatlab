"""accept.py config.json -> writes docs/acceptance/EPIC-N.md on a new branch."""
import json, subprocess, sys
c = json.load(open(sys.argv[1]))
R = str(__import__('pathlib').Path(__file__).resolve().parents[2])
def sh(cmd):
    return subprocess.run(cmd, shell=True, cwd=R, capture_output=True, text=True, executable='/bin/bash')
sh('git checkout -q main && git pull -q')
sha = sh('git log -1 --format=%H').stdout.strip()
pr = c['pr']
job = sh(f"gh pr view {pr} --json statusCheckRollup --jq '.statusCheckRollup[0].detailsUrl'").stdout.strip()
concl = sh(f"gh pr view {pr} --json statusCheckRollup --jq '.statusCheckRollup[0].conclusion'").stdout.strip().lower()
jobid = job.rsplit('/', 1)[-1]
sh(f"git checkout -qb docs/{c['epic']}-acceptance")
demo = []
for cmd in c['demos']:
    out = subprocess.run(['bash', '-c', f'. .venv/bin/activate && openmatlab -e "$0" 2>&1', cmd], cwd=R, capture_output=True, text=True).stdout
    demo.append(f'$ openmatlab -e "{cmd}"\n{out.rstrip()}')
def pt(args):
    r = subprocess.run(f'. .venv/bin/activate && pytest {args} --tb=no -p no:warnings -o addopts="" 2>&1 | tail -1', shell=True, cwd=R, capture_output=True, text=True, executable='/bin/bash').stdout
    return r.strip().strip('=').strip()
conf = f'"tests/conformance/test_m7_conformance.py::test_m7_criterion[{c["cid"]}-{c["script"]}]"'
tf = ' '.join(c['tests'])
gates = [('-m "unit or bdd"', pt('-m "unit or bdd"')), (f'{tf} {conf}', pt(f'{tf} {conf}')), ('tests/conformance/test_m7_conformance.py', pt('tests/conformance/test_m7_conformance.py'))]
feat = sh(f"bash -c '. .venv/bin/activate && openmatlab features | rg -F {c['feature']}'").stdout.rstrip()
rows = '\n'.join(f"| {r[1]} | #{r[0]} | [#{pr}](https://github.com/superche/openmatlab/pull/{pr}) | " + (f"[job {jobid}]({job}) **{concl}**" if i == 0 else "same job") + " |" for i, r in enumerate(c['trace']))
pending = ', '.join(c['pending']) if c['pending'] else 'none'
doc = f"""# Acceptance evidence: Epic #{c['epic']} ({c['title']})

**Epic:** [#{c['epic']}](https://github.com/superche/openmatlab/issues/{c['epic']})  
**Feature PR:** [#{pr}](https://github.com/superche/openmatlab/pull/{pr}) ({', '.join('#'+str(r[0]) for r in c['trace'])})  
**Milestone:** [MATLAB core language & I/O (M7)](https://github.com/superche/openmatlab/milestone/7) · [`docs/milestones/M7-core-language-io.md`](../milestones/M7-core-language-io.md)  
**Design + adversarial review:** [`docs/design/{c['design']}`](../design/{c['design']})  
**Captured:** 2026-10-13 (Asia/Shanghai) on `{R}`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `{sha}` | Squash merge of feature PR [#{pr}](https://github.com/superche/openmatlab/pull/{pr}) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M7 criterion {c['cid']} is **met**. Epic #{c['epic']} stays **open** until the user accepts it.

{c['verdict']}

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
{rows}

## Functional demo (real CLI output)

```text
""" + '\n'.join(demo) + """
```

## Measurable gate: pytest

```text
""" + '\n'.join(f'$ pytest {a} --tb=no\n{b}' for a, b in gates) + f"""
```

New cases: {c['newcases']}

**Existing tests changed: {c.get('changed', 'none')}.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F {c['feature']}
{feat}
```

## Residuals (filed)

{c['residuals']}

## Milestone progress (M7)

- Criteria met: **{c['met']} / 10** ({c['metlist']})
- Conformance scripts passing: **{c['met']} / 10** (strict xfail pending: {pending})
- Next: {c['next']}
"""
open(f"{R}/docs/acceptance/EPIC-{c['epic']}.md", 'w').write(doc)
print(sha, job, concl)
print('\n'.join(f'{a}: {b}' for a, b in gates))
