"""Native desktop and CLI, sharing one dependency directory. See #1081."""
import os
import sys
import tomllib
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

root = Path(SPECPATH).parent
version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
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
if sys.platform == "win32":
    from PyInstaller.utils.win32.versioninfo import (
        VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct,
        VarFileInfo, VarStruct,
    )
    numeric_version = tuple(int(part) for part in version.split(".")) + (0,)
    exe_options["version"] = VSVersionInfo(
        ffi=FixedFileInfo(filevers=numeric_version, prodvers=numeric_version,
                         mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0, 0)),
        kids=[StringFileInfo([StringTable("040904B0", [
            StringStruct("ProductName", "OpenMATLAB"),
            StringStruct("FileDescription", "OpenMATLAB Workbench"),
            StringStruct("ProductVersion", version),
            StringStruct("FileVersion", version),
        ])]), VarFileInfo([VarStruct("Translation", [1033, 1200])])],
    )
cli_exe = EXE(PYZ(cli.pure), cli.scripts, [], name="openmatlab-cli", console=True, **exe_options)
gui_exe = EXE(PYZ(gui.pure), gui.scripts, [], name="OpenMATLAB", console=False, **exe_options)
bundle = COLLECT(gui_exe, cli_exe, cli.binaries, cli.datas, gui.binaries, gui.datas,
                 name="OpenMATLAB", upx=False)
if sys.platform == "darwin":
    app = BUNDLE(bundle, name="OpenMATLAB.app", bundle_identifier="org.openmatlab.workbench",
                 codesign_identity=identity,
                 version=version,
                 info_plist={"NSHighResolutionCapable": True})
