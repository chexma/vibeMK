"""
The HTTP transport's front door.

Over stdio the client already owns the process, so reaching the server means
you had the credentials anyway. Over HTTP it does not: the CheckMK account
lives on the server, and anyone who reaches the port inherits it -- including
the 21 tools that delete things. A bearer token is the minimum that keeps
"the port is open" from meaning "the monitoring system is yours".
"""

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from vibemk.server.http_auth import BearerTokenMiddleware, read_token

TOKEN = "s3cr3t-token-value"


@pytest.fixture
def client() -> TestClient:
    async def ok(_request: Request) -> PlainTextResponse:
        return PlainTextResponse("reached")

    app = Starlette(routes=[Route("/mcp", ok, methods=["GET", "POST"])])
    app.add_middleware(BearerTokenMiddleware, token=TOKEN)
    return TestClient(app)


class TestTheTokenIsRequired:
    def test_a_request_without_authorization_is_refused(self, client):
        response = client.get("/mcp")

        assert response.status_code == 401

    def test_a_wrong_token_is_refused(self, client):
        response = client.get("/mcp", headers={"Authorization": "Bearer not-the-token"})

        assert response.status_code == 401

    def test_a_token_without_the_bearer_scheme_is_refused(self, client):
        response = client.get("/mcp", headers={"Authorization": TOKEN})

        assert response.status_code == 401

    def test_the_right_token_reaches_the_application(self, client):
        response = client.get("/mcp", headers={"Authorization": f"Bearer {TOKEN}"})

        assert response.status_code == 200
        assert response.text == "reached"

    def test_the_scheme_is_matched_case_insensitively(self, client):
        """RFC 9110 calls the scheme case-insensitive, and clients vary."""
        response = client.get("/mcp", headers={"Authorization": f"bearer {TOKEN}"})

        assert response.status_code == 200


class TestTheRefusalSaysNothingUseful:
    def test_the_body_does_not_echo_the_token(self, client):
        response = client.get("/mcp", headers={"Authorization": "Bearer guess-me"})

        assert "guess-me" not in response.text

    def test_the_refusal_names_the_scheme_it_wants(self, client):
        response = client.get("/mcp")

        assert "Bearer" in response.headers.get("WWW-Authenticate", "")


class TestReadingTheTokenFromTheEnvironment:
    def test_a_configured_token_is_returned(self, monkeypatch):
        monkeypatch.setenv("VIBEMK_HTTP_TOKEN", "from-the-environment")

        assert read_token() == "from-the-environment"

    def test_an_absent_token_refuses_to_start(self, monkeypatch):
        """Starting without one would publish the whole catalogue unauthenticated."""
        monkeypatch.delenv("VIBEMK_HTTP_TOKEN", raising=False)

        with pytest.raises(ValueError, match="VIBEMK_HTTP_TOKEN"):
            read_token()

    def test_a_blank_token_refuses_to_start(self, monkeypatch):
        monkeypatch.setenv("VIBEMK_HTTP_TOKEN", "   ")

        with pytest.raises(ValueError, match="VIBEMK_HTTP_TOKEN"):
            read_token()

    def test_a_token_that_is_too_short_refuses_to_start(self, monkeypatch):
        """A guessable token is the same as no token."""
        monkeypatch.setenv("VIBEMK_HTTP_TOKEN", "short")

        with pytest.raises(ValueError, match="at least"):
            read_token()
