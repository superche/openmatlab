"""Gherkin for the MIT-BIH format 212 millivolt conversion (Epic #1008)."""

from __future__ import annotations

import numpy as np
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

pytest.importorskip("numpy")

from openmatlab.host.repl import ReplSession
from openmatlab.libs import mitbih
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]
scenarios("../../features/mitbih_record100.feature")


def _pack_212(s0, s1) -> bytes:
    out = bytearray()
    for a, b in zip(s0, s1):
        a &= 0xFFF
        b &= 0xFFF
        out.extend((a & 0xFF, ((a >> 8) & 0x0F) | (((b >> 8) & 0x0F) << 4), b & 0xFF))
    return bytes(out)


@pytest.fixture
def ctx():
    return {"session": Session.create_default()}


@given("a two-sample format 212 record")
def tiny(ctx, tmp_path):
    samples = np.array([[995, 1011], [1024, 1024]], dtype=np.int32)
    (tmp_path / "a.dat").write_bytes(_pack_212(samples[:, 0], samples[:, 1]))
    lines = [f"rec 2 360 {samples.shape[0]}"]
    for i, name in enumerate(("MLII", "V5")):
        lines.append(
            f"a.dat 212 200 11 1024 {int(samples[0, i])} {mitbih.checksum16(samples[:, i])} 0 {name}"
        )
    (tmp_path / "rec.hea").write_text("\n".join(lines) + "\n", encoding="ascii")
    ReplSession(ctx["session"]).run_line(f"fix = '{tmp_path.as_posix()}';")


@given("a fresh session")
def fresh(ctx):
    pass


@when(parsers.parse('I evaluate "{code}"'))
def do_eval(code, ctx):
    ReplSession(ctx["session"]).run_line(code)


@then(parsers.parse('variable "{name}" equals row [{vals}]'))
def row_eq(ctx, name, vals):
    expected = [float(x.strip()) for x in vals.split(",")]
    got = np.asarray(ctx["session"].workspace.get(name).backend_buffer()).reshape(-1)
    assert list(got) == expected
