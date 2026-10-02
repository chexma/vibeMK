"""
Stdio transport for vibeMK

Reads newline-delimited JSON requests from a stream and writes responses back.
Knows nothing about CheckMK, about tools, or about JSON-RPC semantics beyond
"a request may produce a response, or none".
"""

import json
import sys
from typing import Any, Awaitable, Callable, Dict, Optional, TextIO

from utils import get_logger

logger = get_logger(__name__)

RequestHandler = Callable[[Any], Awaitable[Optional[Dict[str, Any]]]]


class StdioTransport:
    """Serves MCP requests over newline-delimited JSON on a pair of streams."""

    def __init__(self, handle: RequestHandler, stdin: Optional[TextIO] = None, stdout: Optional[TextIO] = None) -> None:
        self._handle = handle
        self._stdin = stdin if stdin is not None else sys.stdin
        self._stdout = stdout if stdout is not None else sys.stdout

    async def run(self) -> None:
        """Read requests until the input ends."""
        logger.info("Transport ready, waiting for requests on stdin")
        while True:
            try:
                line = self._stdin.readline()
                if not line:
                    logger.info("Input closed, shutting down")
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    request = json.loads(line)
                except json.JSONDecodeError:
                    logger.exception("Skipping unparseable line")
                    continue

                response = await self._handle(request)
                if response is not None:
                    self._write(response)

            except KeyboardInterrupt:
                logger.info("Stopped by user")
                break
            except EOFError:
                logger.info("EOF reached, exiting")
                break
            except Exception:  # one bad request must not end the session
                logger.exception("Unexpected error in the transport loop, continuing")
                continue

        logger.info("Transport shutdown complete")

    def _write(self, response: Dict[str, Any]) -> None:
        self._stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        self._stdout.flush()
