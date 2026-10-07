"""Typed dictionary requests for session WebMCP tools."""

from typing import Any, Dict
from typing_extensions import Required, TypedDict


class WebMCPInvokeParams(TypedDict, total=False):
    """Blocking invocation; timeout_seconds is 1–120 (default 60)."""

    tool_ref: Required[str]
    input: Dict[str, Any]
    timeout_seconds: int


class WebMCPStartParams(WebMCPInvokeParams):
    """Start an invocation; timeout_seconds is 1–3600 (default 300)."""


class WebMCPResultParams(TypedDict, total=False):
    """Wait at most 0–30 seconds (default 0) for an invocation result."""

    wait_seconds: int
