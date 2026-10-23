# M12 corpus showcase

`record_m12_corpus_showcase.sh` records a clean fullscreen terminal walkthrough of the
M12 corpus gate (Epic #765): `docs/corpus/REPORT.md` rates, two deprompted T3 golden
samples under `samples/`, and `pytest tests/conformance/test_m12_conformance.py`.

The Rosetta / Octave / chebfun corpus itself is **never committed** (fetched into
`~/.cache/openmatlab-corpus`). The files under `samples/` are short deprompted excerpts
regenerated from that cache for the showcase only.
