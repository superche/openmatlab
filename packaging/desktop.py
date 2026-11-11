import sys

from openmatlab.host.cli import main

if __name__ == "__main__":
    main(["workbench", *sys.argv[1:]])
