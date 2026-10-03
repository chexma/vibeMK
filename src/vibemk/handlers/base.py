"""
Base handler for vibeMK operations
"""

import logging
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, Iterable, List, Optional, TypeVar, Union

from vibemk.api import CheckMKClient
from vibemk.api.exceptions import CheckMKError
from vibemk.utils import get_logger

# Type aliases to avoid import conflicts with built-in 'types' module
ToolArguments = Dict[str, Any]
ToolResult = List[Dict[str, Any]]

logger: logging.Logger = get_logger(__name__)

T = TypeVar("T")
R = TypeVar("R")

_SECONDS_PER_MINUTE = 60
_SECONDS_PER_HOUR = 3600
_SECONDS_PER_DAY = 86400


def time_ago(timestamp: Any) -> Optional[str]:
    """Render a Unix timestamp as "42s ago", "5m ago", "3h ago" or "2d ago".

    None for a missing or zero timestamp: CheckMK sends 0 for an event that
    has not happened yet -- a host never checked, a state that never changed
    -- and counting from 1970 would report that as 56 years ago.
    """
    if not timestamp:
        return None
    try:
        diff = int(time.time() - float(timestamp))
    except (ValueError, TypeError):
        return str(timestamp)

    if diff < _SECONDS_PER_MINUTE:
        return f"{diff}s ago"
    if diff < _SECONDS_PER_HOUR:
        return f"{diff // _SECONDS_PER_MINUTE}m ago"
    if diff < _SECONDS_PER_DAY:
        return f"{diff // _SECONDS_PER_HOUR}h ago"
    return f"{diff // _SECONDS_PER_DAY}d ago"


class BaseHandler(ABC):
    """Base class for all vibeMK handlers"""

    def __init__(self, client: CheckMKClient) -> None:
        self.client = client
        self.logger = logger

    @abstractmethod
    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle tool call and return MCP response content"""

    # A block carrying machine-readable data alongside the prose. The
    # dispatcher lifts it out and sends it as the call's structuredContent;
    # it never reaches the client as a content block.
    STRUCTURED_BLOCK = "_structured"

    # A block saying the call failed. It is the only thing the dispatcher reads
    # to set isError: the leading ❌ it used to look for is also a perfectly
    # good symbol for a CRITICAL service or a failed job, and twice turned a
    # successful lookup into a reported failure.
    ERROR_BLOCK = "_error"

    def structured_response(self, text: str, data: Any) -> List[Dict[str, Any]]:
        """Answer with prose for the reader and data for the model.

        A tool whose result gets acted on -- a host state, a list of problems,
        a metric series -- should not force the caller to parse emoji-marked
        markdown back into values. The text block stays, so a human reading
        the transcript still sees something sensible.
        """
        return [{"type": "text", "text": text}, {"type": self.STRUCTURED_BLOCK, "data": data}]

    # Low on purpose: the Ultimate test instance has two CPUs, and a
    # production site has better things to do than answer one tool call.
    MAX_CONCURRENT_REQUESTS = 4

    def _map_concurrently(
        self, request: Callable[[T], R], items: Iterable[T], max_concurrent: int = MAX_CONCURRENT_REQUESTS
    ) -> List[R]:
        """Apply a blocking request to each item, a few at a time.

        For tools that have to ask CheckMK the same question once per ruleset
        or per object. The client blocks in urllib, so the requests overlap on
        threads, not in the event loop. Results keep the order of the items,
        and the first request that raises does so here, as it would have in a
        plain loop.
        """
        with ThreadPoolExecutor(max_workers=max_concurrent) as pool:
            return list(pool.map(request, items))

    def _if_match_header(self, endpoint: str) -> Dict[str, str]:
        """Build an If-Match header from the current ETag of an object.

        CheckMK requires If-Match on the endpoints that modify an existing
        object and answers 412 when the value is stale — which is the point:
        it stops two writers from silently overwriting each other. Sending the
        wildcard instead is accepted but disables that check.

        Falls back to the wildcard when no ETag can be read, so a failed
        lookup degrades to the previous behaviour rather than blocking a write.
        """
        try:
            current = self.client.get(endpoint)
        except CheckMKError as error:
            self.logger.debug("Could not read ETag for %s: %s", endpoint, error)
            return {"If-Match": "*"}
        return {"If-Match": self._extract_etag(current)}

    @staticmethod
    def _extract_etag(response: Dict[str, Any]) -> str:
        """Read an ETag from a client response, or '*' when there is none.

        CheckMK returns it as an ETag response header; some endpoints also
        carry it in the object body under extensions.meta_data.
        """
        etag = (response.get("headers") or {}).get("ETag")
        if not etag:
            etag = response.get("data", {}).get("extensions", {}).get("meta_data", {}).get("etag")
        return etag or "*"

    def _run_activation(self) -> str:
        """Activate pending changes and return a single status line.

        The write handlers append this to a result that has already said what
        was written, so it stays to one line. Honours NEVER_ACTIVATE_CHANGES
        and never raises: a failed activation must not discard the report of
        a write that did succeed.

        CheckMK runs the activation as a background job, so a success here
        means it was accepted, not that it has finished.
        """
        if self.client.config.never_activate_changes:
            return "🚫 Changes were not activated: NEVER_ACTIVATE_CHANGES is set."

        try:
            pending = self.client.get("domain-types/activation_run/collections/pending_changes")
            if not pending.get("success"):
                return "⚠️ Could not read pending changes; nothing was activated."
            if not pending.get("data", {}).get("value", []):
                return "ℹ️ No pending changes to activate."

            result = self.client.post(
                "domain-types/activation_run/actions/activate-changes/invoke",
                data={
                    "redirect": False,
                    "sites": [self.client.config.site],
                    "force_foreign_changes": True,
                },
                headers={"If-Match": self._extract_etag(pending)},
            )
        except CheckMKError as error:
            return f"⚠️ Activation failed: {error}"
        if not result.get("success"):
            return "⚠️ Activation was not accepted; the changes are still pending."
        return "✅ Changes activated."

    def success_response(self, message: str, data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Create success response"""
        text = f"✅ **{message}**"
        if data:
            text += f"\n\n{self._format_data(data)}"
        return [{"type": "text", "text": text}]

    def error_response(self, message: str, error_details: Optional[str] = None) -> List[Dict[str, Any]]:
        """Create error response"""
        text = f"❌ **{message}**"
        if error_details:
            text += f"\n\n{error_details}"
        return self.error_text(text)

    def error_text(self, text: str) -> List[Dict[str, Any]]:
        """Report a failure in this exact wording; the marker block is what makes it one."""
        return [{"type": "text", "text": text}, {"type": self.ERROR_BLOCK}]

    def info_response(self, message: str, data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Create info response"""
        text = f"ℹ️ **{message}**"
        if data:
            text += f"\n\n{self._format_data(data)}"
        return [{"type": "text", "text": text}]

    def _format_data(self, data: Union[Dict[str, Any], List[Any], str, float, None]) -> str:
        """Format data for display"""
        if isinstance(data, dict):
            formatted_lines: List[str] = []
            for key, value in data.items():
                if isinstance(value, (list, dict)):
                    formatted_lines.append(f"**{key}**: {len(value) if isinstance(value, list) else 'object'}")
                else:
                    formatted_lines.append(f"**{key}**: {value}")
            return "\n".join(formatted_lines)
        return str(data)
