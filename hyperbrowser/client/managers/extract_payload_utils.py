from typing import Any, Dict

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.extract import StartExtractJobParams

from ..schema_utils import inject_resolved_schema
from .serialization_utils import serialize_model_dump_to_dict


def build_extract_start_payload(params: StartExtractJobParams) -> Dict[str, Any]:
    if not params.schema_ and not params.prompt:
        raise HyperbrowserError("Either schema or prompt must be provided")

    payload = serialize_model_dump_to_dict(
        params,
        error_message="Failed to serialize extract start params",
    )
    inject_resolved_schema(payload, key="schema", schema_input=params.schema_)
    return payload
