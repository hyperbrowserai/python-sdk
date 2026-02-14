from typing import Any, Dict

from hyperbrowser.models.agents.browser_use import StartBrowserUseTaskParams

from ..schema_utils import inject_resolved_schema
from .agent_payload_utils import build_agent_start_payload


def build_browser_use_start_payload(params: StartBrowserUseTaskParams) -> Dict[str, Any]:
    payload = build_agent_start_payload(
        params,
        error_message="Failed to serialize browser-use start params",
    )
    inject_resolved_schema(
        payload,
        key="outputModelSchema",
        schema_input=params.output_model_schema,
    )
    return payload
