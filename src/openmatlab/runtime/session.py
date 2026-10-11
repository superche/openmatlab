"""Session — composition root for a matrix-first workbench instance."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from typing import Any, Optional

from openmatlab.host.display import ConsoleDisplay, DisplayPolicy, NullDisplay
from openmatlab.host.plot_surface import HostPlotSurface, PlotSurface, StubPlotSurface
from openmatlab.libs.path import ToolboxPath
from openmatlab.runtime.functions import FunctionResolver
from openmatlab.runtime.workspace import Workspace



def resolve_interactive_plots(explicit: Optional[bool] = None) -> bool:
    """Interactive Matplotlib when requested and not running under CI."""
    if explicit is not None:
        return bool(explicit)
    if os.environ.get("CI", "").lower() in ("1", "true", "yes"):
        return False
    if os.environ.get("GITHUB_ACTIONS", "").lower() in ("1", "true", "yes"):
        return False
    flag = os.environ.get("OPENMATLAB_PLOT_INTERACTIVE", "").lower()
    return flag in ("1", "true", "yes", "on")

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
    def create_default(
        cls, *, interactive_plots: Optional[bool] = None
    ) -> "Session":
        """Wire NumPy + ConsoleDisplay + Matplotlib plot surface when available.

        interactive_plots: explicit override; else OPENMATLAB_PLOT_INTERACTIVE
        unless CI/GITHUB_ACTIONS (always Agg in CI).
        """
        numerics = None
        try:
            from openmatlab.numerics.numpy_backend import NumPyArrayBackend

            numerics = NumPyArrayBackend()
        except ImportError:
            pass

        interactive = resolve_interactive_plots(interactive_plots)
        graphics = None
        plots: PlotSurface = StubPlotSurface()
        try:
            from openmatlab.graphics.matplotlib_backend import MatplotlibGraphicsBackend

            graphics = MatplotlibGraphicsBackend(interactive=interactive)
            plots = HostPlotSurface(graphics)
        except ImportError:
            pass

        ws = Workspace()
        display: DisplayPolicy
        if numerics is not None:
            display = ConsoleDisplay(workspace=ws)
        else:
            display = NullDisplay()
        session = cls(
            workspace=ws,
            display=display,
            numerics=numerics,
            graphics=graphics,
            plots=plots,
        )
        if numerics is not None:
            from openmatlab.libs.numeric_builtins import register_numeric_builtins

            register_numeric_builtins(session.functions)
        return session
