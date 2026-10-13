"""eps(x) is the spacing at |x| (#480)."""

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _r(code):
    s = Session.create_default()
    ReplSession(s).run_line("r = " + code + ";")
    return s.workspace.get("r")


def test_eps_of_double_values():
    assert np.asarray(_r("eps(1000)").backend_buffer()).item() == 2.0 ** -43
    got = np.asarray(_r("eps([1 0 -2 Inf NaN])").backend_buffer())
    assert got[0, :3].tolist() == [2.0 ** -52, 2.0 ** -1074, 2.0 ** -51] and np.isnan(got[0, 3:]).all()
    assert np.asarray(_r("eps").backend_buffer()).item() == 2.0 ** -52
    assert np.asarray(_r("eps(ones(2))").backend_buffer()).shape == (2, 2)


def test_eps_single_and_class():
    assert _r("eps(single(1))").matlab_class() == "single"
    assert np.asarray(_r("eps(single(1))").backend_buffer()).item() == 2.0 ** -23
    assert _r("eps(true)").matlab_class() == "double"


def test_eps_of_integers_errors():
    with pytest.raises(Exception, match="floating point"):
        _r("eps(int8(1))")
