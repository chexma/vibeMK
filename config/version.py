"""The project's version, in one place.

`pyproject.toml` reads it from here (`[tool.setuptools.dynamic]`) and
`MCPConfig` defaults to it, so the number a client sees in the `initialize`
handshake and the number on the distribution cannot drift apart.

Deliberately free of imports: setuptools reads this attribute without
executing the package, which only works while the module stays this simple.
"""

__version__ = "0.5.0"
