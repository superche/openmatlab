"""Session — composition root for a matrix-first workbench instance."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

from openmatlab.host.display import ConsoleDisplay, DisplayPolicy, NullDisplay
from openmatlab.host.plot_surface import PlotSurface, StubPlotSurface
from openmatlab.libs.path import ToolboxPath
from openmatlab.runtime.functions import FunctionResolver
from openmatlab.runtime.workspace import Workspace

if TYPE_CHECKING:
    from openmatlab.graphics.backend import GraphicsBackend
    from openmatlab.numerics.backend import ArrayBackend


@dataclass
class Session:
    """One interactive or script-backed workbench session."""

    workspace: Workspace = field(default_factory=Workspace)
    functions: FunctionResolver = field(default_factory=FunctionResolver)
    path: ToolboxPath = field(default_factory=ToolboxPath)
    display: DisplayPolicy = field(default_factory=NullDisplay)
    plots: PlotSurface = field(default_factory=StubPlotSurface)
    numerics: Optional[Any] = None  # ArrayBackend when wired
    graphics: Optional[Any] = None

    def __post_init__(self) -> None:
        self.functions.path = self.path
        if self.graphics is not None and isinstance(self.plots, StubPlotSurface):
            from openmatlab.host.plot_surface import StubPlotSurface as SPS

            self.plots = SPS(backend=self.graphics)
        if isinstance(self.display, ConsoleDisplay) and self.display.workspace is None:
            self.display.workspace = self.workspace

    @classmethod
    def create_default(cls) -> "Session":
        """CLI/REPL factory: NumPy backend + ConsoleDisplay when NumPy present."""
        numerics = None
        try:
            from openmatlab.numerics.numpy_backend import NumPyArrayBackend

            numerics = NumPyArrayBackend()
        except ImportError:
            numerics = None
        ws = Workspace()
        if numerics is not None:
            display: DisplayPolicy = ConsoleDisplay(workspace=ws)
        else:
            display = NullDisplay()
        return cls(workspace=ws, display=display, numerics=numerics)
