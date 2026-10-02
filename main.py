#!/usr/bin/env python3
"""
vibeMK - CheckMK Monitoring via LLM

A shim over `vibemk_mcp.cli`, kept because `python main.py` is the form every
LLM client configuration in examples/ and INSTALL.md uses. The implementation
moved into the package so that the `vibemk` console script resolves after a
`pip install`: setuptools ships packages, not loose top-level modules.

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

from vibemk_mcp.cli import cli, main, parse_arguments

__all__ = ["cli", "main", "parse_arguments"]


if __name__ == "__main__":
    cli()
