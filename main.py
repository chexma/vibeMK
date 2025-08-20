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

import asyncio
from config import CheckMKConfig
from mcp.server import CheckMKMCPServer
from utils import setup_logging


async def main():
    """Main entry point for vibeMK"""
    
    # Load config to determine debug mode
    config = CheckMKConfig.from_env()
    
    # Setup logging
    setup_logging(debug=config.debug)
    
    # Create and run server
    server = CheckMKMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())