"""Session — composition root for a matrix-first workbench instance."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from openmatlab.host.display import ConsoleDisplay, DisplayPolicy, NullDisplay
from openmatlab.host.plot_surface import HostPlotSurface, PlotSurface, StubPlotSurface
from openmatlab.libs.path import ToolboxPath
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
    numerics: Optional[Any] = None
    graphics: Optional[Any] = None

    def __post_init__(self) -> None:
        self.functions.path = self.path
        if self.graphics is not None and isinstance(self.plots, StubPlotSurface):
            self.plots = HostPlotSurface(self.graphics)
        if isinstance(self.display, ConsoleDisplay) and self.display.workspace is None:
            self.display.workspace = self.workspace

    @classmethod
    def create_default(cls) -> "Session":
        """Wire NumPy + ConsoleDisplay + Matplotlib plot surface when available."""
        numerics = None
        try:
            from openmatlab.numerics.numpy_backend import NumPyArrayBackend

            numerics = NumPyArrayBackend()
        except ImportError:
            pass

        graphics = None
        plots: PlotSurface = StubPlotSurface()
        try:
            from openmatlab.graphics.matplotlib_backend import MatplotlibGraphicsBackend

            graphics = MatplotlibGraphicsBackend(interactive=False)
            plots = HostPlotSurface(graphics)
        except ImportError:
            pass

        ws = Workspace()
        display: DisplayPolicy
        if numerics is not None:
            display = ConsoleDisplay(workspace=ws)
        else:
            display = NullDisplay()
        return cls(
            workspace=ws,
            display=display,
            numerics=numerics,
            graphics=graphics,
            plots=plots,
        )
