from typing import Any, Dict

from hyperbrowser.exceptions import HyperbrowserError


def serialize_model_dump_to_dict(
    model: Any,
    *,
    error_message: str,
    exclude_none: bool = True,
    by_alias: bool = True,
) -> Dict[str, Any]:
    try:
        payload = model.model_dump(exclude_none=exclude_none, by_alias=by_alias)
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            error_message,
            original_error=exc,
        ) from exc
    if type(payload) is not dict:
        raise HyperbrowserError(error_message)
    return payload


def serialize_optional_model_dump_to_dict(
    model: Any,
    *,
    error_message: str,
    exclude_none: bool = True,
    by_alias: bool = True,
) -> Dict[str, Any]:
    if model is None:
        return {}
    return serialize_model_dump_to_dict(
        model,
        error_message=error_message,
        exclude_none=exclude_none,
        by_alias=by_alias,
    )
