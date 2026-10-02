"""
Bearer-token authentication for the HTTP transport.

Over stdio the client starts the process, so reaching the server already
implies the right to use it. Over HTTP it does not: the CheckMK account lives
in the server's environment, and every caller inherits it -- including the
tools that delete hosts, users and rules. A token is the minimum that keeps an
open port from meaning an open monitoring system.

This is deliberately small. It is not an authorization system: one token
grants the whole catalogue. For per-user access the SDK offers OAuth hooks
(`token_verifier`, `auth_server_provider`), which need an authorization server
this project does not ship.
"""

import os
import secrets
from typing import Any, Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

TOKEN_VARIABLE = "VIBEMK_HTTP_TOKEN"

# Short enough to type, long enough that guessing is not a strategy.
MINIMUM_TOKEN_LENGTH = 16

_SCHEME = "bearer"


def read_token() -> str:
    """The token the HTTP transport will require, from the environment.

    Raises rather than defaulting: a server that starts without one would
    publish 154 tools, 21 of them destructive, to anyone who can reach the
    port.
    """
    token = (os.environ.get(TOKEN_VARIABLE) or "").strip()
    if not token:
        raise ValueError(
            f"{TOKEN_VARIABLE} must be set to serve over HTTP. "
            "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
    if len(token) < MINIMUM_TOKEN_LENGTH:
        raise ValueError(f"{TOKEN_VARIABLE} must be at least {MINIMUM_TOKEN_LENGTH} characters")
    return token


class BearerTokenMiddleware(BaseHTTPMiddleware):
    """Refuses any request that does not carry the configured bearer token."""

    def __init__(self, app: Any, token: str) -> None:
        super().__init__(app)
        self._token = token

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if not self._authorized(request.headers.get("Authorization")):
            # Nothing about the presented value is echoed back: a refusal
            # should not help the next guess.
            return JSONResponse(
                {"error": "unauthorized"},
                status_code=401,
                headers={"WWW-Authenticate": 'Bearer realm="vibeMK"'},
            )
        return await call_next(request)

    def _authorized(self, header: str | None) -> bool:
        if not header:
            return False
        scheme, _, presented = header.partition(" ")
        if scheme.lower() != _SCHEME:
            return False
        # Constant time, so a wrong token does not leak how much of it was right.
        return secrets.compare_digest(presented.strip(), self._token)
