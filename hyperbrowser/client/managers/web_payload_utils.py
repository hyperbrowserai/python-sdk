from typing import Any, Dict

from hyperbrowser.models import FetchParams, WebSearchParams

from ..schema_utils import inject_web_output_schemas
from .serialization_utils import serialize_model_dump_to_dict


def build_web_fetch_payload(params: FetchParams) -> Dict[str, Any]:
    payload = serialize_model_dump_to_dict(
        params,
        error_message="Failed to serialize web fetch params",
    )
    inject_web_output_schemas(payload, params.outputs.formats if params.outputs else None)
    return payload


def build_web_search_payload(params: WebSearchParams) -> Dict[str, Any]:
    return serialize_model_dump_to_dict(
        params,
        error_message="Failed to serialize web search params",
    )
