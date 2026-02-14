from typing import Any, Dict, Tuple

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.extension import CreateExtensionParams

from ..file_utils import ensure_existing_file_path, format_file_path_for_error
from .serialization_utils import serialize_model_dump_to_dict


def normalize_extension_create_input(params: Any) -> Tuple[str, Dict[str, Any]]:
    if type(params) is not CreateExtensionParams:
        raise HyperbrowserError("params must be CreateExtensionParams")
    try:
        raw_file_path = params.file_path
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            "params.file_path is invalid",
            original_error=exc,
        ) from exc

    payload = serialize_model_dump_to_dict(
        params,
        error_message="Failed to serialize extension create params",
    )
    payload.pop("filePath", None)

    file_path_display = format_file_path_for_error(raw_file_path)
    file_path = ensure_existing_file_path(
        raw_file_path,
        missing_file_message=f"Extension file not found at path: {file_path_display}",
        not_file_message=f"Extension file path must point to a file: {file_path_display}",
    )
    return file_path, payload
