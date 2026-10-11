import pytest

from openmatlab import __version__

pytestmark = pytest.mark.unit


def test_version():
    assert __version__ == "0.0.2"
