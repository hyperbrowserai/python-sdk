from typing import Any, Dict

from hyperbrowser.models.agents.browser_use import StartBrowserUseTaskParams

from ..schema_utils import inject_resolved_schema
from .serialization_utils import serialize_model_dump_to_dict


def build_browser_use_start_payload(params: StartBrowserUseTaskParams) -> Dict[str, Any]:
    payload = serialize_model_dump_to_dict(
        params,
        error_message="Failed to serialize browser-use start params",
    )
    inject_resolved_schema(
        payload,
        key="outputModelSchema",
        schema_input=params.output_model_schema,
    )
    return payload
