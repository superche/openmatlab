# Acceptance evidence: Epic #532 (command syntax and workspace commands)

**Epic:** [#532](https://github.com/superche/openmatlab/issues/532)  
**Feature PR:** [#574](https://github.com/superche/openmatlab/pull/574) (#545, #546)  
**Milestone:** [MATLAB core language & I/O (M7)](https://github.com/superche/openmatlab/milestone/7) · [`docs/milestones/M7-core-language-io.md`](../milestones/M7-core-language-io.md)  
**Design + adversarial review:** [`docs/design/EPIC-532-command-syntax.md`](../design/EPIC-532-command-syntax.md)  
**Captured:** 2026-10-13 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `1059fd45a5626bbeca249c3e123add8c8066a5fd` | Squash merge of feature PR [#574](https://github.com/superche/openmatlab/pull/574) |
| Evidence merge tip | `65bfd229fceb7615449768e42a7355e377dfd725` | Squash merge of [#575](https://github.com/superche/openmatlab/pull/575); re-run from here or `main` |

## Verdict

**Ready for user acceptance.** M7 criterion C03 is **met**. Epic #532 stays **open** until the user accepts it.

`name arg ...` command syntax follows MATLAB's lexical rule. A variable name is re-read as an expression (`a -1`).

These now work: `clear` (names, wildcards, `-regexp`, `all`, `global`), `clearvars -except`, `who`/`whos` (values and listings), `format short`/`long`, `clc`, `help`, `pwd`/`cd`/`dir`/`ls`, `evalc`, `which` in command form, and `isvarname`/`iskeyword`.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| command syntax `name arg ...` (lexer + CommandStmt, variable re-read) | #545 | [#574](https://github.com/superche/openmatlab/pull/574) | [job 115135860016](https://github.com/superche/openmatlab/actions/runs/38348675462/job/115135860016) **success** |
| clear/clearvars/who/whos/format/clc/help/pwd/cd/dir/ls/evalc/which/isvarname | #546 | [#574](https://github.com/superche/openmatlab/pull/574) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "format long; pi, format short; pi"
ans =

3.141592653589793

ans =

3.1416
$ openmatlab -e "a = 3; a -1"
ans =

2
$ openmatlab -e "x1 = 1; x2 = 2; y = 3; clear x*; who"
Your variables are:

y
$ openmatlab -e "q = [1 2 3]; whos"
  Name      Size            Bytes  Class     Attributes

  q         1x3                24  double
$ openmatlab -e "disp 'hello world'"
hello world
$ openmatlab -e "t = evalc('which sin')"
t =

built-in (builtin/sin)
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1182 passed, 2 deselected, 7 xfailed in 14.35s
$ pytest tests/unit/test_command_syntax.py tests/bdd/test_command_syntax_bdd.py "tests/conformance/test_m7_conformance.py::test_m7_criterion[C03-m7_c03_command_syntax]" --tb=no
34 passed in 0.45s
$ pytest tests/conformance/test_m7_conformance.py --tb=no
4 passed, 7 xfailed in 0.48s
```

New cases: 28 unit tests (`tests/unit/test_command_syntax.py`), 5 Gherkin scenarios (`features/command_syntax.feature`), and conformance `m7_c03_command_syntax` (23 checks) flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F lang.command_syntax
lang.command_syntax              lang       done     command syntax and workspace commands
```

## Residuals (filed)

- [#573](https://github.com/superche/openmatlab/issues/573) (p2): G/compact/rat format modes, per-session format state, `dir`/`ls` column layout, `more`/`diary`.

## Milestone progress (M7)

- Criteria met: **3 / 10** (C01–C03)
- Conformance scripts passing: **3 / 10** (strict xfail pending: C04–C10)
- Next: Epic #533 (C04 file I/O)
