"""usage: epicdocs.py CID script epic residual feat_id feat_name depends notes unit_test bdd_test next_text met_count"""
import sys, re, json
cid, script, epic, resid, fid, fname, deps, notes, unit, bdd, nxt, met = sys.argv[1:13]
R=str(__import__('pathlib').Path(__file__).resolve().parents[2])+'/'
import os; sys.path.insert(0, R+'scripts/epic'); from milestones import MS; M=MS[os.environ.get('MS','m7')]
p=R+M['manifest']; s=open(p).read()
s2=re.sub(r'("%s": \("%s", "p\d", \[[^\]]*\], )"pending"' % (cid, script), r'\1"met"', s); assert s2!=s; open(p,'w').write(s2)
p=R+M['doc']; s=open(p).read()
s2=re.sub(r'(\| %s \|.*\| )pending \|' % script, r'\1met (Epic #%s; residual #%s) |' % (epic, resid), s); assert s2!=s
m=re.search(r'\*\*\d+ / \d+\*\* criteria met: (.*?)\. Next: .*', s2); assert m
total=len(re.findall(r'^\| [A-Z]\d+ \|', s2, re.M))
s2=s2.replace(m.group(0), '**%s / %s** criteria met: %s, %s (Epic #%s). Next: %s' % (met, total, m.group(1), cid, epic, nxt))
open(p,'w').write(s2)
p=R+'docs/feature_map.yaml'; s=open(p).read()
entry=f'''  - id: {fid}
    layer: {fid.split('.')[0]}
    name: {fname}
    status: done
    depends_on: [{deps}]
    notes: "{notes}"
    tests: [{unit}, {bdd}]

  - id: runtime.array_assign_range'''
s=s.replace('  - id: runtime.array_assign_range', entry, 1); open(p,'w').write(s)
p=R+'docs/test_catalog.yaml'; s=open(p).read()
base=unit.split('/')[-1][5:-3]
entry=f'''  - id: tc.{base}
    kind: unit
    title: {fname} (Epic #{epic})
    features: [{fid}]
    use_cases: [uc.matrix_first_repl]
    impl: {unit}
    status: active
    env: unit

  - id: tc.{base}_bdd
    kind: bdd
    title: {fname} Gherkin scenarios (Epic #{epic})
    features: [{fid}]
    use_cases: [uc.matrix_first_repl]
    impl: {bdd}
    status: active
    env: unit

  - id: tc.script_local_functions'''
s=s.replace('  - id: tc.script_local_functions', entry, 1); open(p,'w').write(s)
