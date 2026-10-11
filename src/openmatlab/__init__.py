"""OpenMATLAB: clean-room MATLAB-compatible language/runtime from public specs."""

__version__ = "0.0.1"

from openmatlab.evaluator import run
from openmatlab.parser import parse

__all__ = ["__version__", "parse", "run"]
