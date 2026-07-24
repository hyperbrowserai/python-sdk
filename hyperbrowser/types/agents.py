from typing import Any, Dict, List, Optional

from typing_extensions import Required, TypedDict

from hyperbrowser.models.consts import (
    BrowserUseLlm,
    BrowserUseVersion,
    ClaudeComputerUseLlm,
    CuaLlm,
    GeminiComputerUseLlm,
    GrokComputerUseLlm,
    GrokReasoningEffort,
    HyperAgentLlm,
    HyperAgentVersion,
)

from ._json import JSONSchemaObjectInput
from .session import CreateSessionParams


class BrowserUseApiKeys(TypedDict, total=False):
    """Provider API keys for a Browser Use task."""

    openai: Optional[str]
    anthropic: Optional[str]
    google: Optional[str]


class StartBrowserUseTaskParams(TypedDict, total=False):
    """Parameters for starting a Browser Use task."""

    task: Required[str]
    version: Optional[BrowserUseVersion]
    llm: Optional[BrowserUseLlm]
    session_id: Optional[str]
    validate_output: Optional[bool]
    use_vision: Optional[bool]
    use_vision_for_planner: Optional[bool]
    max_actions_per_step: Optional[int]
    max_input_tokens: Optional[int]
    planner_llm: Optional[BrowserUseLlm]
    page_extraction_llm: Optional[BrowserUseLlm]
    planner_interval: Optional[int]
    max_steps: Optional[int]
    max_failures: Optional[int]
    initial_actions: Optional[List[Dict[str, Dict[str, Any]]]]
    sensitive_data: Optional[Dict[str, str]]
    message_context: Optional[str]
    output_model_schema: Optional[JSONSchemaObjectInput]
    keep_browser_open: Optional[bool]
    session_options: Optional[CreateSessionParams]
    use_custom_api_keys: Optional[bool]
    api_keys: Optional[BrowserUseApiKeys]


class ClaudeComputerUseApiKeys(TypedDict, total=False):
    """Provider API keys for a Claude Computer Use task."""

    anthropic: Optional[str]


class StartClaudeComputerUseTaskParams(TypedDict, total=False):
    """Parameters for starting a Claude Computer Use task."""

    task: Required[str]
    llm: Optional[ClaudeComputerUseLlm]
    session_id: Optional[str]
    max_failures: Optional[int]
    max_steps: Optional[int]
    keep_browser_open: Optional[bool]
    session_options: Optional[CreateSessionParams]
    use_custom_api_keys: Optional[bool]
    api_keys: Optional[ClaudeComputerUseApiKeys]
    use_computer_action: Optional[bool]


class GeminiComputerUseApiKeys(TypedDict, total=False):
    """Provider API keys for a Gemini Computer Use task."""

    google: Optional[str]


class StartGeminiComputerUseTaskParams(TypedDict, total=False):
    """Parameters for starting a Gemini Computer Use task."""

    task: Required[str]
    llm: Optional[GeminiComputerUseLlm]
    session_id: Optional[str]
    max_failures: Optional[int]
    max_steps: Optional[int]
    keep_browser_open: Optional[bool]
    session_options: Optional[CreateSessionParams]
    use_custom_api_keys: Optional[bool]
    use_computer_action: Optional[bool]
    api_keys: Optional[GeminiComputerUseApiKeys]


class GrokComputerUseApiKeys(TypedDict, total=False):
    """Provider API keys for a Grok Computer Use task."""

    xai: Optional[str]


class StartGrokComputerUseTaskParams(TypedDict, total=False):
    """Parameters for starting a Grok Computer Use task."""

    task: Required[str]
    llm: Optional[GrokComputerUseLlm]
    reasoning_effort: Optional[GrokReasoningEffort]
    session_id: Optional[str]
    max_failures: Optional[int]
    max_steps: Optional[int]
    keep_browser_open: Optional[bool]
    session_options: Optional[CreateSessionParams]
    use_custom_api_keys: Optional[bool]
    api_keys: Optional[GrokComputerUseApiKeys]
    use_computer_action: Optional[bool]


class CuaApiKeys(TypedDict, total=False):
    """Provider API keys for an OpenAI CUA task."""

    openai: Optional[str]


class StartCuaTaskParams(TypedDict, total=False):
    """Parameters for starting an OpenAI CUA task."""

    task: Required[str]
    llm: Optional[CuaLlm]
    session_id: Optional[str]
    max_failures: Optional[int]
    max_steps: Optional[int]
    keep_browser_open: Optional[bool]
    session_options: Optional[CreateSessionParams]
    use_custom_api_keys: Optional[bool]
    api_keys: Optional[CuaApiKeys]
    use_computer_action: Optional[bool]


class HyperAgentApiKeys(TypedDict, total=False):
    """Provider API keys for a HyperAgent task."""

    openai: Optional[str]
    anthropic: Optional[str]
    google: Optional[str]


class StartHyperAgentTaskParams(TypedDict, total=False):
    """Parameters for starting a HyperAgent task."""

    version: Optional[HyperAgentVersion]
    task: Required[str]
    llm: Optional[HyperAgentLlm]
    session_id: Optional[str]
    max_steps: Optional[int]
    enable_visual_mode: Optional[bool]
    keep_browser_open: Optional[bool]
    session_options: Optional[CreateSessionParams]
    use_custom_api_keys: Optional[bool]
    api_keys: Optional[HyperAgentApiKeys]


__all__ = [
    "BrowserUseApiKeys",
    "ClaudeComputerUseApiKeys",
    "CuaApiKeys",
    "GeminiComputerUseApiKeys",
    "GrokComputerUseApiKeys",
    "HyperAgentApiKeys",
    "StartBrowserUseTaskParams",
    "StartClaudeComputerUseTaskParams",
    "StartCuaTaskParams",
    "StartGeminiComputerUseTaskParams",
    "StartGrokComputerUseTaskParams",
    "StartHyperAgentTaskParams",
]
