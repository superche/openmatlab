"""Gherkin for PNG imread size and class (Epic #1020)."""

from __future__ import annotations

import struct
import zlib

import numpy as np
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

pytest.importorskip("numpy")

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]
scenarios("../../features/bbbc038_imread.feature")

_SIG = b"\x89PNG\r\n\x1a\n"


def _png(width, height, color, scanlines: bytes) -> bytes:
    def chunk(tag, body):
        crc = zlib.crc32(tag + body) & 0xFFFFFFFF
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, color, 0, 0, 0)
    return _SIG + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(scanlines)) + chunk(b"IEND", b"")


@pytest.fixture
def ctx():
    return {"session": Session.create_default()}


@given("a 2 by 2 grayscale png")
def gray(ctx, tmp_path):
    path = tmp_path / "g.png"
    raw = bytes([0, 10, 20, 0, 30, 40])
    path.write_bytes(_png(2, 2, 0, raw))
    ReplSession(ctx["session"]).run_line(f"png = '{path.as_posix()}';")


@given("a 1 by 1 rgba png")
def rgba(ctx, tmp_path):
    path = tmp_path / "c.png"
    path.write_bytes(_png(1, 1, 6, bytes([0, 9, 8, 7, 6])))
    ReplSession(ctx["session"]).run_line(f"png = '{path.as_posix()}';")


@when(parsers.parse('I evaluate the png "{code}"'))
def do_eval(code, ctx):
    ReplSession(ctx["session"]).run_line(code)


@then(parsers.parse('the png variable "{name}" equals row [{vals}]'))
def row_eq(ctx, name, vals):
    expected = [float(item.strip()) for item in vals.split(",")]
    got = np.asarray(ctx["session"].workspace.get(name).backend_buffer()).reshape(-1)
    assert list(got) == expected
