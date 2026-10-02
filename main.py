#!/usr/bin/env python3
"""
vibeMK - CheckMK Monitoring via LLM

A shim over `vibemk.server.cli`, kept because `python /path/to/main.py` is
the form existing LLM client configurations use. The code lives in the
`vibemk` package under src/; an installed vibeMK is started with `vibemk`.

Run from a checkout without installing, src/ is not on the import path, so
the shim puts it there first.

Copyright (C) 2024 Andre <chexma@gmx.de>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import sys
from pathlib import Path

# The checks below run before anything from src/ is imported, so this file
# has to stay parseable by the oldest interpreter a client might start it with:
# no syntax newer than Python 3.8, which vibeMK supported until 0.5.
#
# A stdio server that dies on import shows the user only "server disconnected";
# the traceback goes to a client log nobody reads. Say what to do instead.
_MINIMUM_PYTHON = (3, 10)

# Sliced so the comparison is not narrowed away by type checkers that assume
# the configured interpreter version.
if sys.version_info[:2] < _MINIMUM_PYTHON:
    sys.stderr.write(
        "vibeMK needs Python 3.10 or newer, but was started with Python %d.%d (%s).\n"
        "Point the LLM client configuration at a newer interpreter, or install vibeMK\n"
        "with 'pipx install vibemk' or 'uv tool install vibemk' and start the 'vibemk' command.\n"
        % (sys.version_info[0], sys.version_info[1], sys.executable)
    )
    sys.exit(1)

try:
    import jsonschema  # noqa: F401
    import mcp  # noqa: F401
except ImportError as missing:
    sys.stderr.write(
        "vibeMK cannot start: %s.\n"
        "Install its dependencies into the Python the client starts (%s):\n"
        "    %s -m pip install -r %s\n"
        % (missing, sys.executable, sys.executable, Path(__file__).resolve().parent / "requirements.txt")
    )
    sys.exit(1)

_SRC = Path(__file__).resolve().parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from vibemk.server.cli import cli, main, parse_arguments

__all__ = ["cli", "main", "parse_arguments"]


if __name__ == "__main__":
    cli()
