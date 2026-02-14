from typing import Any

from pydantic import BaseModel

from .serialization_utils import serialize_model_dump_to_dict


def build_computer_action_payload(params: Any) -> Any:
    if isinstance(params, BaseModel):
        return serialize_model_dump_to_dict(
            params,
            error_message="Failed to serialize computer action params",
            by_alias=True,
            exclude_none=True,
        )
    return params
