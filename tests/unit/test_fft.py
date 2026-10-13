"""FFT family (M3-E1, Epic #625)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _ws(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return lambda n: np.asarray(s.workspace.get(n).backend_buffer())


def test_fft_vector_matches_dft():
    g = _ws("X = fft([1 2 3 4]); Y = fft([1 2 3 4]');")
    assert np.allclose(g("X"), [[10, -2 + 2j, -2, -2 - 2j]])
    assert g("Y").shape == (4, 1)


def test_fft_pad_truncate_and_dim():
    g = _ws("a = fft([1 2 3], 5); b = fft([1 2 3 4], 2); A = [1 2; 3 4]; c = fft(A); d = fft(A, [], 2); e = fft(A, 3, 2);")
    assert g("a").shape == (1, 5) and np.allclose(g("b"), [[3, -1]])
    assert np.allclose(g("c"), [[4, 6], [-2, -2]]) and np.allclose(g("d"), [[3, -1], [7, -1]])
    assert g("e").shape == (2, 3)


def test_ifft_roundtrip_and_symmetric():
    g = _ws("x = rand(3, 7); r = max(abs(ifft(fft(x)) - x), [], 'all'); s = ifft(fft([1 2 3]), 'symmetric'); i = isreal(s);")
    assert g("r")[0, 0] < 1e-12 and np.allclose(g("s"), [[1, 2, 3]]) and g("i")[0, 0]


def test_fft2_ifft2_fftn():
    g = _ws("A = magic(4); F = fft2(A); B = real(ifft2(F)); G = fftn(A); P = fft2(A, 8, 8);")
    assert np.allclose(g("F"), np.fft.fft2(np.array([[16, 2, 3, 13], [5, 11, 10, 8], [9, 7, 6, 12], [4, 14, 15, 1]])))
    assert np.allclose(g("B"), g("B").round()) and np.allclose(g("G"), g("F")) and g("P").shape == (8, 8)


def test_fftshift_ifftshift_nextpow2():
    g = _ws("a = fftshift([1 2 3 4 5]); b = ifftshift([1 2 3 4 5]); c = fftshift([1 2; 3 4]); d = fftshift([1 2 3; 4 5 6], 2);"
            " n = nextpow2([100 1 0 1024 0.3]);")
    assert g("a").tolist() == [[4, 5, 1, 2, 3]] and g("b").tolist() == [[3, 4, 5, 1, 2]]
    assert g("c").tolist() == [[4, 3], [2, 1]] and g("d").tolist() == [[3, 1, 2], [6, 4, 5]]
    assert g("n").tolist() == [[7, 0, 0, 10, -1]]


def test_fft_errors_and_empty():
    s = Session.create_default()
    ReplSession(s).run_line("try, fft(1, -1); e = ''; catch err, e = err.identifier; end; z = fft([]);")
    assert s.workspace.get("e").text == "MATLAB:fftfcn:lengthNotNonnegInt"
    assert np.asarray(s.workspace.get("z").backend_buffer()).size == 0
