"""Graphics: backend protocol + matplotlib implementation."""

from openmatlab.graphics.backend import GraphicsBackend
from openmatlab.graphics.matplotlib_backend import GraphicsError, MatplotlibGraphicsBackend

__all__ = ["GraphicsBackend", "MatplotlibGraphicsBackend", "GraphicsError"]
