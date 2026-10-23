"""Global imbinarize (Otsu) and 2-D bwareaopen (Epic #1021). Synthetic images only."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.libs.imbinarize import RGB_WEIGHTS, _as_gray, component_areas, otsu_level
from openmatlab.runtime.evaluator import EvalError

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _run(code: str) -> ReplSession:
    session = ReplSession()
    session.run_line(code)
    return session


def _num(session: ReplSession, name: str) -> np.ndarray:
    return np.asarray(session.session.workspace.get(name).backend_buffer())


def test_default_imbinarize_matches_hand_otsu():
    pixels = np.array([0, 0, 10, 10, 200, 200], dtype=np.uint8)
    assert otsu_level(pixels.reshape(1, -1)) == pytest.approx(10 / 255)
    session = _run(
        "I = uint8([0 0 10 10 200 200]); level = graythresh(I); "
        "BW = imbinarize(I); BW2 = imbinarize(I, level); "
        "n = sum(BW(:)); same = sum(abs(double(BW(:)) - double(BW2(:)))); t = level * 255;"
    )
    assert _num(session, "t") == pytest.approx(10)
    assert _num(session, "n") == 2
    assert _num(session, "same") == 0
    assert list(_num(session, "BW").reshape(-1)) == [False, False, False, False, True, True]


def test_constant_images_use_level_zero():
    session = _run(
        "z = imbinarize(uint8(zeros(2, 3))); o = imbinarize(uint8(7 * ones(2, 3))); "
        "nz = sum(z(:)); no = sum(o(:));"
    )
    assert _num(session, "nz") == 0
    assert _num(session, "no") == 6


def test_scalar_threshold_is_strictly_greater():
    session = _run(
        "I = uint8([127 128]); BW = imbinarize(I, 0.5); n = sum(BW(:)); "
        "k = double(strcmp(class(BW), 'logical'));"
    )
    assert list(_num(session, "BW").reshape(-1)) == [False, True]
    assert _num(session, "n") == 1
    assert _num(session, "k") == 1


def test_rgb_uses_documented_weights_and_matches_gray_channel_when_equal():
    assert RGB_WEIGHTS == (0.2989, 0.5870, 0.1140)
    session = _run(
        "R = uint8([10 20]); Z = uint8(zeros(1, 2)); "
        "I = uint8(cat(3, R, Z, Z)); g = uint8(round(0.2989 * double(R))); "
        "BW = imbinarize(I, 0); n = sum(BW(:)); "
        "E = uint8(cat(3, R, R, R)); ER = imbinarize(E); EG = imbinarize(R); "
        "same = sum(abs(double(ER(:)) - double(EG(:))));"
    )
    assert _num(session, "n") == 2
    assert _num(session, "g").reshape(-1).tolist() == [3, 6]
    assert _as_gray(_num(session, "I")).reshape(-1).tolist() == [3, 6]
    assert _num(session, "same") == 0


def test_tie_takes_the_smallest_bin():
    session = _run("I = uint8([0 0 0 255 255 255]); level = graythresh(I); t = level * 255;")
    assert _num(session, "t") == pytest.approx(0)


def test_rejected_threshold_forms():
    with pytest.raises(EvalError, match="adaptive"):
        _run("imbinarize(uint8([0 255]), 'adaptive');")
    with pytest.raises(EvalError, match="threshold matrix"):
        _run("imbinarize(uint8([0 255; 255 0]), [0.2 0.8; 0.2 0.8]);")
    with pytest.raises(EvalError, match="\\[0, 1\\]"):
        _run("imbinarize(uint8([0 255]), 1.5);")
    with pytest.raises(EvalError, match="Too many input arguments"):
        _run("imbinarize(uint8([0 255]), 0.5, 'extra');")


def test_bwareaopen_drops_components_smaller_than_p():
    session = _run(
        "BW = logical([1 0 0 0; 1 0 1 1; 0 0 1 1]); "
        "BW2 = bwareaopen(BW, 3); n = sum(BW2(:)); kept = sum(BW2(1, :));"
    )
    assert _num(session, "n") == 4
    assert _num(session, "kept") == 0
    areas = component_areas(np.array([[1, 0, 0, 0], [1, 0, 1, 1], [0, 0, 1, 1]], dtype=bool), 8)
    assert sorted(int(v) for v in areas) == [2, 4]


def test_area_equal_to_p_is_kept_and_default_conn_is_8():
    session = _run(
        "BW = logical([1 1 0 0]); A = bwareaopen(BW, 2); B = bwareaopen(BW, 3); "
        "D = logical([1 0; 0 1]); E = bwareaopen(D, 2); F = bwareaopen(D, 2, 4); G = bwareaopen(D, 2, 8); "
        "na = sum(A(:)); nb = sum(B(:)); ne = sum(E(:)); nf = sum(F(:)); ng = sum(G(:));"
    )
    assert _num(session, "na") == 2
    assert _num(session, "nb") == 0
    assert _num(session, "ne") == 2
    assert _num(session, "ng") == 2
    assert _num(session, "nf") == 0


def test_bwareaopen_rejects_3d_and_other_connectivity():
    with pytest.raises(EvalError, match="2-D"):
        _run("bwareaopen(ones(2, 2, 2), 1);")
    with pytest.raises(EvalError, match="connectivity"):
        _run("bwareaopen(logical([1 1; 0 0]), 1, 6);")
    with pytest.raises(EvalError, match="connectivity"):
        _run("bwareaopen(logical([1 0; 0 1]), 1, ones(3));")
    with pytest.raises(EvalError, match="nonnegative"):
        _run("bwareaopen(logical([1 0]), -1);")
