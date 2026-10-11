"""Session — composition root for a matrix-first workbench instance.

Wires Workspace, FunctionResolver, optional ArrayBackend, DisplayPolicy,
PlotSurface, and ToolboxPath without implementing eval yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from openmatlab.host.display import DisplayPolicy, NullDisplay
from openmatlab.host.plot_surface import PlotSurface, StubPlotSurface
from openmatlab.libs.path import ToolboxPath
from openmatlab.graphics.backend import GraphicsBackend
from openmatlab.numerics.backend import ArrayBackend
from openmatlab.runtime.functions import FunctionResolver
from openmatlab.runtime.workspace import Workspace


@dataclass
class Session:
    """One interactive or script-backed workbench session."""

    workspace: Workspace = field(default_factory=Workspace)
    functions: FunctionResolver = field(default_factory=FunctionResolver)
    path: ToolboxPath = field(default_factory=ToolboxPath)
    display: DisplayPolicy = field(default_factory=NullDisplay)
    plots: PlotSurface = field(default_factory=StubPlotSurface)
    numerics: Optional[ArrayBackend] = None
    graphics: Optional[GraphicsBackend] = None

    def __post_init__(self) -> None:
        # Ensure resolver can see toolbox path when path/.m loading lands
        self.functions.path = self.path
        if self.graphics is not None and isinstance(self.plots, StubPlotSurface):
            self.plots = StubPlotSurface(backend=self.graphics)

    @classmethod
    def create_default(cls) -> "Session":
        """Factory for CLI/REPL — stubs only at architecture stage."""
        return cls()
