"""Run the shipped executables outside the checkout, with no source PYTHONPATH."""
import argparse
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile


def binary_arch(path):
    with Path(path).open("rb") as stream:
        magic = stream.read(4)
        if magic == b"\xcf\xfa\xed\xfe":
            return "arm64" if struct.unpack("<I", stream.read(4))[0] == 0x100000C else "other"
        if magic[:2] == b"MZ":
            stream.seek(0x3C)
            stream.seek(struct.unpack("<I", stream.read(4))[0])
            if stream.read(4) == b"PE\0\0":
                return "x64" if struct.unpack("<H", stream.read(2))[0] == 0x8664 else "other"
    raise ValueError(f"Unknown executable format: {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--arch", choices=["arm64", "x64"], required=True)
    args = parser.parse_args()
    suffix = ".exe" if sys.platform == "win32" else ""
    cli = args.directory.resolve() / ("openmatlab-cli" + suffix)
    gui = args.directory.resolve() / ("OpenMATLAB" + suffix)
    for path in (cli, gui):
        assert binary_arch(path) == args.arch, path
    env = dict(os.environ, MPLBACKEND="Agg")
    env.pop("PYTHONPATH", None)
    with tempfile.TemporaryDirectory() as directory:
        def run(executable, *arguments):
            result = subprocess.run([str(executable), *arguments], cwd=directory,
                                    env=env, text=True, capture_output=True, timeout=90)
            print(result.stdout, end="")
            if result.returncode:
                raise RuntimeError(f"{arguments}: {result.returncode}\n{result.stderr}")
            return result.stdout
        run(cli, "-e", "A=[1 2;3 4]; assert(sum(A(:))==10);")
        run(cli, "features", "--layer", "host")
        run(cli, "cases", "--kind", "unit")
        run(cli, "-e", "plot([1 2 3],[1 4 9]); saveas(gcf,'smoke.png');")
        assert (Path(directory) / "smoke.png").stat().st_size > 100
        env["MPLBACKEND"] = "TkAgg"
        run(gui, "--demo-ms", "1500")
    print(f"Frozen CLI, resources, plot export and Workbench smoke passed ({args.arch})")


if __name__ == "__main__":
    main()
