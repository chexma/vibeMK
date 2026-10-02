"""
vibeMK - CheckMK monitoring over the Model Context Protocol

Everything lives under this one package: api (the CheckMK REST client),
config, handlers (one per tool family), utils, checkmk_types and server (the
MCP protocol layer and the `vibemk` command).
"""

from vibemk.config.version import __version__

__all__ = ["__version__"]
