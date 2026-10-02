#!/usr/bin/env python3
"""
vibeMK - CheckMK Monitoring via LLM

Copyright (C) 2024 Andre <andre@example.com>

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

import argparse
import asyncio
import os
import sys

from utils import setup_logging
from vibemk_mcp.server import CheckMKMCPServer

DEFAULT_HTTP_PORT = 8765


def parse_arguments(argv=None) -> argparse.Namespace:
    """Read the transport settings from the command line and the environment.

    stdio stays the default: it is how an MCP client launches a server it owns.
    HTTP is for hosting one centrally, so that clients need nothing installed.
    """
    parser = argparse.ArgumentParser(prog="vibemk", description="CheckMK monitoring over MCP")
    parser.add_argument(
        "--transport",
        choices=("stdio", "http"),
        default=os.environ.get("VIBEMK_TRANSPORT", "stdio"),
        help="stdio (default) or http for Streamable HTTP",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("VIBEMK_HTTP_HOST", "127.0.0.1"),
        help="address to bind in http mode (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("VIBEMK_HTTP_PORT", DEFAULT_HTTP_PORT)),
        help=f"port to bind in http mode (default: {DEFAULT_HTTP_PORT})",
    )
    parser.add_argument(
        "--path",
        default=os.environ.get("VIBEMK_HTTP_PATH", "/mcp"),
        help="URL path to serve in http mode (default: /mcp)",
    )
    return parser.parse_args(argv)


async def main(argv=None):
    """Main entry point for vibeMK"""
    options = parse_arguments(argv)

    # Force UTF-8 on stdio regardless of the launching environment. The MCP
    # protocol and tool output (emoji, accents) are UTF-8; without this the
    # server crashes on Windows with UnicodeEncodeError when the parent process
    # doesn't set PYTHONIOENCODING.
    for stream in (sys.stdout, sys.stdin, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    # Setup logging with debug mode if LOGFILE is specified for better troubleshooting
    debug_mode = bool(os.environ.get("LOGFILE"))  # Enable debug logging when file logging is active
    setup_logging(debug=debug_mode)

    # Create and run server (CheckMK config loaded on first tool call)
    server = CheckMKMCPServer()
    if options.transport == "http":
        try:
            await server.run_http(host=options.host, port=options.port, path=options.path)
        except ValueError as error:
            # A missing or weak token is a configuration mistake, not a crash.
            print(f"vibemk: {error}", file=sys.stderr)
            raise SystemExit(2) from None
    else:
        await server.run()


if __name__ == "__main__":
    asyncio.run(main())
