"""
Safe construction of REST API paths

Host names, rule ids, user names and the like reach the API path straight from
tool arguments, which the model fills in from what it reads -- including text
an attacker may control. Interpolated raw, a value such as
"x/../../objects/user_config/admin" or "x?y" addresses a different endpoint
than the tool means to call.
"""

import urllib.parse
from typing import Any

# Segments a server resolves as path navigation rather than as a name.
_NAVIGATION_SEGMENTS = (".", "..")


class UnsafePathError(ValueError):
    """A value or endpoint would address something other than what it names."""


def path_segment(value: Any) -> str:
    """Encode a value so it fills exactly one segment of an API path.

    Everything outside the unreserved characters is percent-encoded, slash
    included, so the value cannot open a new segment, a query or a fragment.
    "~" is unreserved and survives, which keeps CheckMK folder paths such as
    "~linux~web" intact. "." and ".." are refused outright: encoding does not
    help there, because servers normalise percent-encoded dots as well.
    """
    text = str(value)
    if not text:
        raise UnsafePathError("An API path segment must not be empty")
    if text in _NAVIGATION_SEGMENTS:
        raise UnsafePathError(f"Not a valid name for an API object: {text!r}")
    return urllib.parse.quote(text, safe="")


def check_endpoint(endpoint: str) -> None:
    """Refuse an endpoint that would navigate away from where it points.

    The second line of defence behind path_segment: an endpoint built without
    it still cannot climb out of its collection or smuggle in a query string.
    Query parameters belong in the client's params argument, which encodes
    them.
    """
    if "?" in endpoint or "#" in endpoint:
        raise UnsafePathError(f"Query or fragment in an API path: {endpoint!r}")
    for segment in endpoint.split("/"):
        if urllib.parse.unquote(segment) in _NAVIGATION_SEGMENTS:
            raise UnsafePathError(f"Path navigation in an API path: {endpoint!r}")
