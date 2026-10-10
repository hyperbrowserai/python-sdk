from typing import Optional, Union
from urllib.parse import quote

from hyperbrowser.client._request import coerce_request, dump_request
from hyperbrowser.models.webmcp import (
    WebMCPInvocation,
    WebMCPInvokeParams,
    WebMCPInvokeResult,
    WebMCPResultParams,
    WebMCPStartParams,
    WebMCPToolsResponse,
)
from hyperbrowser.types.webmcp import (
    WebMCPInvokeParams as WebMCPInvokeParamsDict,
    WebMCPResultParams as WebMCPResultParamsDict,
    WebMCPStartParams as WebMCPStartParamsDict,
)


class WebMCPManager:
    """Discover and invoke page tools in sessions created with enable_web_mcp=True."""

    def __init__(self, client):
        self._client = client

    def _url(self, session_id: str, suffix: str) -> str:
        return self._client._build_url(
            f"/session/{quote(session_id, safe='')}/webmcp{suffix}"
        )

    def list_tools(self, session_id: str) -> WebMCPToolsResponse:
        """Discover document-bound tools across the session's tabs and frames."""
        response = self._client.transport.get(
            self._url(session_id, "/tools"), timeout=max(self._client.timeout, 40)
        )
        return WebMCPToolsResponse(**response.data)

    def invoke(
        self,
        session_id: str,
        params: Union[WebMCPInvokeParamsDict, WebMCPInvokeParams],
    ) -> WebMCPInvokeResult:
        """Invoke once and wait. A form can return awaiting_submission with a handle.

        This POST is never automatically retried: losing its response can leave the
        outcome unknown, and repeating it could duplicate a side effect.
        """
        request = coerce_request(params, WebMCPInvokeParams)
        response = self._client.transport.post(
            self._url(session_id, "/invoke"),
            data=dump_request(request, WebMCPInvokeParams),
            timeout=max(self._client.timeout, request.timeout_seconds + 35),
        )
        return WebMCPInvokeResult(**response.data)

    def start(
        self,
        session_id: str,
        params: Union[WebMCPStartParamsDict, WebMCPStartParams],
    ) -> WebMCPInvocation:
        """Start once and return a handle; use get_result to observe its outcome."""
        response = self._client.transport.post(
            self._url(session_id, "/invocations"),
            data=dump_request(params, WebMCPStartParams),
            timeout=max(self._client.timeout, 40),
        )
        return WebMCPInvocation(**response.data)

    def get_result(
        self,
        session_id: str,
        invocation_id: str,
        params: Optional[Union[WebMCPResultParamsDict, WebMCPResultParams]] = None,
    ) -> WebMCPInvocation:
        """Read or long-poll once. Running/awaiting_submission can remain pending.

        Handles are in memory. Terminal results expire after 10 minutes and may
        be evicted sooner; browser shutdown or receiver restart also loses them.
        """
        request = coerce_request(
            params if params is not None else {}, WebMCPResultParams
        )
        response = self._client.transport.get(
            self._url(session_id, f"/invocations/{quote(invocation_id, safe='')}"),
            params=dump_request(request, WebMCPResultParams),
            timeout=max(self._client.timeout, request.wait_seconds + 20),
        )
        return WebMCPInvocation(**response.data)

    def cancel(self, session_id: str, invocation_id: str) -> WebMCPInvocation:
        """Request best-effort cancellation. Completion can win; side effects persist."""
        response = self._client.transport.post(
            self._url(
                session_id, f"/invocations/{quote(invocation_id, safe='')}/cancel"
            ),
            timeout=max(self._client.timeout, 20),
        )
        return WebMCPInvocation(**response.data)
