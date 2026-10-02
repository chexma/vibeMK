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

_SRC = Path(__file__).resolve().parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from vibemk.server.cli import cli, main, parse_arguments

__all__ = ["cli", "main", "parse_arguments"]


if __name__ == "__main__":
    cli()
