"""Native desktop and CLI, sharing one dependency directory. See #1081."""
import os
import sys
import tomllib
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

root = Path(SPECPATH).parent
identity = os.environ.get("APPLE_SIGNING_IDENTITY") or None
options = dict(
    pathex=[str(root / "src")],
    datas=[(str(root / "docs" / name), "docs") for name in
           ("feature_map.yaml", "test_catalog.yaml")] +
          [(str(root / "LICENSE"), ".")] + collect_data_files("openmatlab"),
    hiddenimports=collect_submodules("openmatlab") + ["matplotlib.backends.backend_tkagg"],
    excludes=["pytest", "pytest_cov", "pytest_bdd"],
    hooksconfig={"matplotlib": {"backends": ["TkAgg", "Agg"]}},
)
cli = Analysis([str(root / "packaging/cli.py")], **options)
gui = Analysis([str(root / "packaging/desktop.py")], **options)
exe_options = dict(exclude_binaries=True, upx=False, codesign_identity=identity,
                   target_arch="arm64" if sys.platform == "darwin" else None)
cli_exe = EXE(PYZ(cli.pure), cli.scripts, [], name="openmatlab-cli", console=True, **exe_options)
gui_exe = EXE(PYZ(gui.pure), gui.scripts, [], name="OpenMATLAB", console=False, **exe_options)
bundle = COLLECT(gui_exe, cli_exe, cli.binaries, cli.datas, gui.binaries, gui.datas,
                 name="OpenMATLAB", upx=False)
if sys.platform == "darwin":
    app = BUNDLE(bundle, name="OpenMATLAB.app", bundle_identifier="org.openmatlab.workbench",
                 codesign_identity=identity,
                 version=tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"],
                 info_plist={"NSHighResolutionCapable": True})
