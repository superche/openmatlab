# Feature `done` criteria — Epic #9 (#126) / Issue #128

## lang.continue → done
- Observable: continue in for/while; nested innermost; outside → EvalError
- break outside also EvalError (hardening)
- Tests: tests/unit/test_continue.py
- Non-goals: labeled continue, return, switch
