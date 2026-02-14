from typing import Any, Dict

from .serialization_utils import serialize_model_dump_to_dict


def build_agent_start_payload(params: Any, *, error_message: str) -> Dict[str, Any]:
    return serialize_model_dump_to_dict(
        params,
        error_message=error_message,
    )
